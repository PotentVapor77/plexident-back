# api/dashboard/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
import logging
import pytz

from api.dashboard.serializers import (
    DashboardStatsSerializer,
    EstadisticasCitasSerializer,
    FiltroFechasSerializer,
    KPIsSerializer,
    OverviewSerializer
)
from api.dashboard.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

# ✅✅✅ TIMEZONE DE ECUADOR ✅✅✅
ECUADOR_TZ = pytz.timezone('America/Guayaquil')


def get_fecha_local_ecuador():
    """Retorna la fecha actual en Ecuador (UTC-5)"""
    return timezone.now().astimezone(ECUADOR_TZ).date()


class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet para el dashboard de Plexident con soporte para filtros RF-06.6
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['GET'])
    def stats(self, request):
        """
        GET /api/dashboard/stats/
        
        Dashboard principal con estadísticas según el rol del usuario
        
        Query Params (RF-06.6):
            - fecha_inicio (opcional): Fecha inicio en formato YYYY-MM-DD
            - fecha_fin (opcional): Fecha fin en formato YYYY-MM-DD
            - periodo (opcional): 'dia', 'semana', 'mes', 'trimestre', 'anio'
        
        Roles soportados:
            - Administrador: Vista completa de la clínica
            - Odontologo: Vista enfocada en atención clínica
            - Asistente: Vista operativa y de apoyo
        
        Ejemplos:
            GET /api/dashboard/stats/
            GET /api/dashboard/stats/?periodo=semana
            GET /api/dashboard/stats/?fecha_inicio=2026-01-01&fecha_fin=2026-01-31
        """
        try:
            # Obtener parámetros de filtro
            fecha_inicio = request.query_params.get('fecha_inicio')
            fecha_fin = request.query_params.get('fecha_fin')
            periodo = request.query_params.get('periodo', 'mes')

            # Validar fechas si se proporcionan
            if fecha_inicio or fecha_fin:
                serializer = FiltroFechasSerializer(data={
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                })
                if not serializer.is_valid():
                    return Response(
                        {'error': 'Formato de fechas inválido', 'detalles': serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Obtener datos del servicio
            data = DashboardService.get_dashboard_data(
                user=request.user,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                periodo=periodo
            )

            # Agregar timestamp
            data['timestamp'] = timezone.now().isoformat()
            data['usuario'] = {
                'username': request.user.username,
                'nombre_completo': f"{request.user.nombres} {request.user.apellidos}" if hasattr(request.user, 'nombres') else request.user.username
            }

            # Validar respuesta con serializer
            response_serializer = DashboardStatsSerializer(data=data)
            if response_serializer.is_valid():
                return Response({
                    'success': True,
                    'status_code': 200,
                    'message': 'Dashboard obtenido correctamente',
                    'data': response_serializer.validated_data,
                    'errors': None
                }, status=status.HTTP_200_OK)
            else:
                # Si hay error en serializer, devolver data sin validar (con warning)
                logger.warning(f"Dashboard data no pasó validación: {response_serializer.errors}")
                return Response({
                    'success': True,
                    'status_code': 200,
                    'message': 'Dashboard obtenido correctamente',
                    'data': data,
                    'errors': None
                }, status=status.HTTP_200_OK)

        except ValueError as ve:
            logger.error(f"Error de validación en dashboard stats: {str(ve)}")
            return Response({
                'success': False,
                'status_code': 400,
                'message': 'Parámetros inválidos',
                'data': None,
                'errors': str(ve)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error en dashboard stats: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'status_code': 500,
                'message': 'Error interno del servidor',
                'data': None,
                'errors': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def overview(self, request):
        """
        GET /api/dashboard/overview/
        
        Vista general del dashboard (métricas principales rápidas)
        No requiere filtros, siempre retorna datos del día actual
        
        Útil para widgets o vistas resumidas
        """
        try:
            from api.dashboard.repositories.dashboard_repository import DashboardRepository
            
            fechas = DashboardRepository.get_fechas_filtro()
            
            overview_data = {
                'total_pacientes': DashboardRepository.get_total_pacientes(),
                'pacientes_activos': DashboardRepository.get_pacientes_activos(),
                'citas_hoy': DashboardRepository.get_citas_hoy(fechas['hoy']),
                'signos_vitales_hoy': DashboardRepository.get_signos_vitales_hoy(fechas['hoy']),
                'rol': request.user.rol if hasattr(request.user, 'rol') else 'DESCONOCIDO',
                'fecha': fechas['hoy'].isoformat(),
                'timestamp': timezone.now().isoformat()
            }

            return Response({
                'success': True,
                'status_code': 200,
                'message': 'Overview obtenido correctamente',
                'data': overview_data,
                'errors': None
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error en dashboard overview: {str(e)}")
            return Response({
                'success': False,
                'status_code': 500,
                'message': 'Error obteniendo overview',
                'data': None,
                'errors': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def citas_stats(self, request):
        """
        GET /api/dashboard/citas-stats/
        
        ✅ RF-06.2: Estadísticas detalladas de citas con distribución por estado
        
        Query Params (RF-06.6):
            - fecha_inicio (requerido): Fecha inicio YYYY-MM-DD
            - fecha_fin (requerido): Fecha fin YYYY-MM-DD
        
        Response incluye:
            - Distribución por estado (para gráficos pie/donut)
            - Estadísticas numéricas detalladas
            - Promedio diario
            - Evolución día a día (para gráfico de líneas)
        
        Ejemplo:
            GET /api/dashboard/citas-stats/?fecha_inicio=2026-01-01&fecha_fin=2026-01-31
        """
        try:
            # Validar parámetros requeridos
            fecha_inicio = request.query_params.get('fecha_inicio')
            fecha_fin = request.query_params.get('fecha_fin')

            if not fecha_inicio or not fecha_fin:
                return Response({
                    'success': False,
                    'status_code': 400,
                    'message': 'Los parámetros fecha_inicio y fecha_fin son requeridos',
                    'data': None,
                    'errors': 'fecha_inicio y fecha_fin requeridos'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validar formato
            serializer = FiltroFechasSerializer(data={
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            })
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'status_code': 400,
                    'message': 'Formato de fechas inválido',
                    'data': None,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # Convertir strings a dates
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()

            # Validar rango lógico
            if fecha_inicio_obj > fecha_fin_obj:
                return Response({
                    'success': False,
                    'status_code': 400,
                    'message': 'fecha_inicio no puede ser mayor que fecha_fin',
                    'data': None,
                    'errors': 'Rango de fechas inválido'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Obtener estadísticas completas
            stats = DashboardService.get_estadisticas_citas_completas(
                fecha_inicio_obj,
                fecha_fin_obj
            )

            # Agregar metadata
            stats['metadata'] = {
                'usuario': request.user.username,
                'rol': request.user.rol if hasattr(request.user, 'rol') else None,
                'timestamp': timezone.now().isoformat()
            }

            # Validar respuesta
            response_serializer = EstadisticasCitasSerializer(data=stats)
            if response_serializer.is_valid():
                return Response({
                    'success': True,
                    'status_code': 200,
                    'message': 'Estadísticas de citas obtenidas correctamente',
                    'data': response_serializer.validated_data,
                    'errors': None
                }, status=status.HTTP_200_OK)
            else:
                logger.warning(f"Citas stats no pasó validación: {response_serializer.errors}")
                return Response({
                    'success': True,
                    'status_code': 200,
                    'message': 'Estadísticas de citas obtenidas correctamente',
                    'data': stats,
                    'errors': None
                }, status=status.HTTP_200_OK)

        except ValueError as ve:
            logger.error(f"Error de validación en citas stats: {str(ve)}")
            return Response({
                'success': False,
                'status_code': 400,
                'message': 'Formato de fecha inválido',
                'data': None,
                'errors': 'Use formato YYYY-MM-DD'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error en citas stats: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'status_code': 500,
                'message': 'Error interno del servidor',
                'data': None,
                'errors': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def periodos_disponibles(self, request):
        """
        GET /api/dashboard/periodos-disponibles/
        
        ✅ CORREGIDO: Retorna periodos con fechas en hora LOCAL de Ecuador
        """
        # ✅✅✅ USAR FECHA LOCAL DE ECUADOR (NO UTC) ✅✅✅
        hoy = get_fecha_local_ecuador()
        
        # Calcular fechas de periodos predefinidos
        # Hoy
        fecha_hoy_inicio = hoy
        fecha_hoy_fin = hoy
        
        # Semana Actual (Lunes a Domingo)
        inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes
        fin_semana = inicio_semana + timedelta(days=6)       # Domingo
        
        # Mes Actual
        inicio_mes = hoy.replace(day=1)
        if hoy.month == 12:
            fin_mes = hoy.replace(month=12, day=31)
        else:
            fin_mes = (hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1))
        
        # Trimestre Actual (desde inicio del trimestre hasta hoy)
        mes_actual = hoy.month
        trimestre = (mes_actual - 1) // 3
        mes_inicio_trimestre = trimestre * 3 + 1
        inicio_trimestre = hoy.replace(month=mes_inicio_trimestre, day=1)
        fin_trimestre = hoy  # ✅ Hasta hoy, no hasta fin de trimestre
        
        # Año Actual
        inicio_anio = hoy.replace(month=1, day=1)
        fin_anio = hoy.replace(month=12, day=31)

        periodos = {
            'hoy': {
                'label': 'Hoy',
                'fecha_inicio': fecha_hoy_inicio.isoformat(),  # ✅ YYYY-MM-DD sin timezone
                'fecha_fin': fecha_hoy_fin.isoformat(),
                'periodo': 'hoy'
            },
            'semana_actual': {
                'label': 'Semana Actual',
                'fecha_inicio': inicio_semana.isoformat(),
                'fecha_fin': fin_semana.isoformat(),
                'periodo': 'semana_actual'
            },
            'mes_actual': {
                'label': 'Mes Actual',
                'fecha_inicio': inicio_mes.isoformat(),
                'fecha_fin': fin_mes.isoformat(),
                'periodo': 'mes_actual'
            },
            'trimestre_actual': {
                'label': 'Trimestre Actual',
                'fecha_inicio': inicio_trimestre.isoformat(),
                'fecha_fin': fin_trimestre.isoformat(),
                'periodo': 'trimestre_actual'
            },
            'anio_actual': {
                'label': 'Año Actual',
                'fecha_inicio': inicio_anio.isoformat(),
                'fecha_fin': fin_anio.isoformat(),
                'periodo': 'anio_actual'
            }
        }

        return Response({
            'success': True,
            'status_code': 200,
            'message': 'Periodos disponibles obtenidos',
            'data': {
                'periodos': periodos,
                'fecha_actual': hoy.isoformat(),  # ✅ Fecha local Ecuador
                'hoy_display': hoy.strftime('%d %b %Y'),
                'timezone': 'America/Guayaquil'  # ✅ Info adicional
            },
            'errors': None
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'])
    def kpis(self, request):
        """
        GET /api/dashboard/kpis/
        
        ✅ RF-06.1: Endpoint dedicado para KPIs principales
        Retorna solo las métricas clave sin gráficos ni tablas
        
        Query Params:
            - periodo (opcional): 'dia', 'semana', 'mes', 'trimestre', 'anio'
        
        Ideal para widgets pequeños o cards de métricas
        """
        try:
            from api.dashboard.repositories.dashboard_repository import DashboardRepository
            
            periodo = request.query_params.get('periodo', 'mes')
            fechas = DashboardRepository.get_fechas_filtro(periodo=periodo)
            
            hoy = fechas['hoy']
            fecha_inicio = fechas['fecha_inicio']
            fecha_fin = fechas['fecha_fin']

            kpis = {
                # ✅ RF-06.1: KPIs requeridos
                'total_pacientes_activos': DashboardRepository.get_pacientes_activos(),
                'citas_hoy': DashboardRepository.get_citas_hoy(hoy),
                'citas_semana': DashboardRepository.get_citas_semana(fecha_inicio, fecha_fin),
                'promedio_citas_diarias': DashboardRepository.get_promedio_citas_diarias(fecha_inicio, fecha_fin),
                
                # KPIs adicionales
                'citas_asistidas_hoy': DashboardRepository.get_citas_asistidas_hoy(hoy),
                'citas_en_atencion': DashboardRepository.get_citas_en_atencion_hoy(hoy),
                'signos_vitales_hoy': DashboardRepository.get_signos_vitales_hoy(hoy),
                
                # Metadata
                'periodo': periodo,
                'fecha_inicio': fecha_inicio.isoformat(),
                'fecha_fin': fecha_fin.isoformat(),
                'fecha_actual': hoy.isoformat()
            }

            return Response({
                'success': True,
                'status_code': 200,
                'message': 'KPIs obtenidos correctamente',
                'data': kpis,
                'errors': None
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error en KPIs endpoint: {str(e)}")
            return Response({
                'success': False,
                'status_code': 500,
                'message': 'Error obteniendo KPIs',
                'data': None,
                'errors': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def diagnosticos_frecuentes(self, request):
        """
        GET /api/dashboard/diagnosticos-frecuentes/
        
        ✅ RF-06.3: Estadísticas de diagnósticos más frecuentes
        
        Query Params:
            - fecha_inicio (requerido): Fecha inicio YYYY-MM-DD
            - fecha_fin (requerido): Fecha fin YYYY-MM-DD
            - limit (opcional): Número de resultados (default: 10)
        
        Retorna:
            - Top diagnósticos más frecuentes
            - Conteo y porcentaje
            - Distribución por diente
        
        Ejemplo:
            GET /api/dashboard/diagnosticos-frecuentes/?fecha_inicio=2026-01-01&fecha_fin=2026-01-31&limit=5
        """
        try:
            # Validar parámetros requeridos
            fecha_inicio = request.query_params.get('fecha_inicio')
            fecha_fin = request.query_params.get('fecha_fin')
            limit = int(request.query_params.get('limit', 10))

            if not fecha_inicio or not fecha_fin:
                return Response({
                    'success': False,
                    'status_code': 400,
                    'message': 'Los parámetros fecha_inicio y fecha_fin son requeridos',
                    'data': None,
                    'errors': 'fecha_inicio y fecha_fin requeridos'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validar formato
            serializer = FiltroFechasSerializer(data={
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            })
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'status_code': 400,
                    'message': 'Formato de fechas inválido',
                    'data': None,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # Convertir strings a dates
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()

            # Validar rango lógico
            if fecha_inicio_obj > fecha_fin_obj:
                return Response({
                    'success': False,
                    'status_code': 400,
                    'message': 'fecha_inicio no puede ser mayor que fecha_fin',
                    'data': None,
                    'errors': 'Rango de fechas inválido'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Obtener estadísticas de diagnósticos frecuentes
            data = DashboardService.get_diagnosticos_frecuentes_data(
                fecha_inicio_obj, 
                fecha_fin_obj, 
                limit
            )

            # Agregar metadata
            data['metadata'].update({
                'usuario': request.user.username,
                'rol': request.user.rol if hasattr(request.user, 'rol') else None,
                'timestamp': timezone.now().isoformat(),
                'query_params': {
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                    'limit': limit
                }
            })

            return Response({
                'success': True,
                'status_code': 200,
                'message': 'Diagnósticos frecuentes obtenidos correctamente',
                'data': data,
                'errors': None
            }, status=status.HTTP_200_OK)

        except ValueError as ve:
            logger.error(f"Error de validación en diagnósticos frecuentes: {str(ve)}")
            return Response({
                'success': False,
                'status_code': 400,
                'message': 'Formato de fecha inválido',
                'data': None,
                'errors': 'Use formato YYYY-MM-DD'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error en diagnósticos frecuentes: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'status_code': 500,
                'message': 'Error interno del servidor',
                'data': None,
                'errors': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def estadisticas_avanzadas(self, request):
        """
        GET /api/dashboard/estadisticas-avanzadas/
        
        ✅ RF-06.3: Estadísticas combinadas avanzadas
        """
        try:
            # Validar parámetros
            fecha_inicio = request.query_params.get('fecha_inicio')
            fecha_fin = request.query_params.get('fecha_fin')
            tipo = request.query_params.get('tipo', 'completo')

            if not fecha_inicio or not fecha_fin:
                return Response({
                    'success': False,
                    'status_code': 400,
                    'message': 'Los parámetros fecha_inicio y fecha_fin son requeridos',
                    'data': None,
                    'errors': 'fecha_inicio y fecha_fin requeridos'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validar formato
            serializer = FiltroFechasSerializer(data={
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            })
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'status_code': 400,
                    'message': 'Formato de fechas inválido',
                    'data': None,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # Convertir strings a dates
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()

            if fecha_inicio_obj > fecha_fin_obj:
                return Response({
                    'success': False,
                    'status_code': 400,
                    'message': 'fecha_inicio no puede ser mayor que fecha_fin',
                    'data': None,
                    'errors': 'Rango de fechas inválido'
                }, status=status.HTTP_400_BAD_REQUEST)

            from api.dashboard.repositories.dashboard_repository import DashboardRepository
            
            # Construir respuesta según tipo
            if tipo == 'diagnosticos':
                data = {
                    'tipo': 'diagnosticos',
                    'periodo': {
                        'fecha_inicio': fecha_inicio,
                        'fecha_fin': fecha_fin
                    },
                    'diagnosticos_frecuentes': DashboardRepository.get_diagnosticos_frecuentes(
                        fecha_inicio_obj, fecha_fin_obj, 15
                    ),
                    'diagnosticos_por_diente': DashboardRepository.get_diagnosticos_frecuentes_por_diente(
                        fecha_inicio_obj, fecha_fin_obj, 5
                    ),
                }
            else:  # completo
                data = {
                    'tipo': 'completo',
                    'periodo': {
                        'fecha_inicio': fecha_inicio,
                        'fecha_fin': fecha_fin
                    },
                    'diagnosticos': {
                        'frecuentes': DashboardRepository.get_diagnosticos_frecuentes(
                            fecha_inicio_obj, fecha_fin_obj, 10
                        ),
                        'por_diente': DashboardRepository.get_diagnosticos_frecuentes_por_diente(
                            fecha_inicio_obj, fecha_fin_obj, 3
                        )
                    },
                    'citas': DashboardRepository.get_estadisticas_detalladas_citas(
                        fecha_inicio_obj, fecha_fin_obj
                    ),
                    'resumen': {
                        'total_diagnosticos': len(
                            DashboardRepository.get_diagnosticos_frecuentes(
                                fecha_inicio_obj, fecha_fin_obj, 1000
                            )
                        ),
                        'citas_completadas': DashboardRepository.get_citas_asistidas_mes(
                            fecha_inicio_obj.replace(day=1)
                        )
                    }
                }

            # Agregar metadata
            data['metadata'] = {
                'usuario': request.user.username,
                'rol': request.user.rol if hasattr(request.user, 'rol') else None,
                'timestamp': timezone.now().isoformat(),
                'tipo_consulta': tipo
            }

            return Response({
                'success': True,
                'status_code': 200,
                'message': 'Estadísticas avanzadas obtenidas correctamente',
                'data': data,
                'errors': None
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error en estadísticas avanzadas: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'status_code': 500,
                'message': 'Error interno del servidor',
                'data': None,
                'errors': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
