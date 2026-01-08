# api/odontogram/views/odontograma_views.py

import logging
from django.shortcuts import get_object_or_404
from django.db.models import Q, Prefetch
from django.utils import timezone
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from api.odontogram.models import (
    IndicadoresSaludBucal,
    Paciente,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma,
)
from django.core.cache import cache
from rest_framework.pagination import CursorPagination
from rest_framework.pagination import PageNumberPagination
from api.odontogram.serializers import (
    PacienteBasicSerializer,
    PacienteDetailSerializer,
    DienteDetailSerializer,
    SuperficieDentalListSerializer,
    DiagnosticoDentalListSerializer,
    DiagnosticoDentalDetailSerializer,
    DiagnosticoDentalCreateSerializer,
    HistorialOdontogramaSerializer,
)

from api.odontogram.services.odontogram_services import IndicadoresSaludBucalService, OdontogramaService, IndiceCariesService
from api.odontogram.serializers.bundle_serializers import FHIRBundleSerializer
from api.odontogram.serializers.serializers import DienteSerializer, IndicadoresSaludBucalSerializer
from api.users.permissions import UserBasedPermission
from django.db import models

logger = logging.getLogger(__name__)


class PacienteViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar pacientes"""
    permission_classes = [IsAuthenticated, UserBasedPermission]
    permission_model_name = 'paciente'

    def get_queryset(self):
        queryset = Paciente.objects.all()
        
        # Filtro por búsqueda
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombres__icontains=search) |
                Q(apellidos__icontains=search) |
                Q(cedula_pasaporte__icontains=search)
            )
        
        return queryset.prefetch_related(
            'dientes__superficies__diagnosticos__diagnostico_catalogo',
            'dientes__superficies__diagnosticos__odontologo'
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PacienteDetailSerializer
        return PacienteBasicSerializer

    @action(detail=True, methods=['get'])
    def odontograma(self, request, pk=None):
        """
        GET /api/pacientes/{id}/odontograma/
        """
        paciente = self.get_object()
        
        dientes = Diente.objects.filter(
            paciente=paciente
        ).prefetch_related(
            Prefetch(
                'superficies',
                queryset=SuperficieDental.objects.prefetch_related(
                    Prefetch(
                        'diagnosticos',
                        queryset=DiagnosticoDental.objects.filter(
                            activo=True
                        ).select_related('diagnostico_catalogo', 'odontologo')
                    )
                )
            )
        ).order_by('codigo_fdi')
        
        dientes_data = DienteSerializer(dientes, many=True).data
        
        response_data = {
            'paciente': {
                'id': str(paciente.id),
                'nombres': paciente.nombres,
                'apellidos': paciente.apellidos,
                'cedula_pasaporte': paciente.cedula_pasaporte,
            },
            'dientes': dientes_data
        }
        
        logger.info(f"Odontograma cargado para paciente {paciente.id}: {len(dientes_data)} dientes")
        
        return Response(response_data)
    
    @action(detail=True, methods=['get'], url_path='indices-cpo-ceo')
    def indices_cpo_ceo(self, request, pk=None):
        """
        GET /api/odontogram/pacientes/{id}/indices-cpo-ceo/
        """
        paciente = self.get_object()
        indices = IndiceCariesService.calcular_indices_paciente(str(paciente.id))
        return Response(indices, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def por_version(self, request):
        """
        GET /api/odontogram/historial/por_version/?version_id=...
        
        Retorna TODOS los cambios de una versión específica SIN paginación
        Ideal para reconstruir estado del odontograma en ese momento
        """
        version_id = request.query_params.get('version_id')
        
        if not version_id:
            return Response(
                {'error': 'version_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cache_key = f'historial:version:{version_id}'
        data = cache.get(cache_key)
        
        if not data:
            cambios = HistorialOdontograma.objects.filter(
                version_id=version_id
            ).select_related(
                'odontologo',
                'diente',
                'diente__paciente'
            ).order_by('fecha', 'id')
            
            serializer = self.get_serializer(cambios, many=True)
            data = serializer.data
            
            # Caché de 1 hora (versiones no cambian)
            cache.set(cache_key, data, timeout=3600)
        
        return Response({
            'version_id': version_id,
            'count': len(data),
            'cambios': data
        })
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        GET /api/odontogram/historial/estadisticas/?paciente_id=...
        
        """
        paciente_id = request.query_params.get('paciente_id')
        
        if not paciente_id:
            return Response(
                {'error': 'paciente_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cache_key = f'historial:stats:{paciente_id}'
        stats = cache.get(cache_key)
        
        if not stats:
            from django.db.models import Count, Min, Max
            
            stats = HistorialOdontograma.objects.filter(
                diente__paciente_id=paciente_id
            ).aggregate(
                total_cambios=Count('id'),
                total_versiones=Count('version_id', distinct=True),
                primer_cambio=Min('fecha'),
                ultimo_cambio=Max('fecha'),
                cambios_por_tipo=Count('tipo_cambio')
            )
            
            # Caché de 10 minutos
            cache.set(cache_key, stats, timeout=600)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def versiones(self, request):
        """
        GET /api/odontogram/historial/versiones/?paciente_id=...
        
        Retorna lista de versiones únicas (guardados completos)
        con caché de 5 minutos
        """
        paciente_id = request.query_params.get('paciente_id')
        
        if not paciente_id:
            return Response(
                {'error': 'paciente_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cache_key = f'historial:versiones:{paciente_id}'
        versiones = cache.get(cache_key)
        
        if not versiones:
            # Consulta optimizada con anotaciones
            versiones = HistorialOdontograma.objects.filter(
                diente__paciente_id=paciente_id
            ).values(
                'version_id',
                'fecha'
            ).annotate(
                odontologo_nombre=models.F('odontologo__nombres'),
                odontologo_apellido=models.F('odontologo__apellidos'),
                total_cambios=models.Count('id')
            ).order_by('-fecha').distinct()[:50]
            
            versiones = list(versiones)
            
            # Guardar en caché por 5 minutos
            cache.set(cache_key, versiones, timeout=300)
        
        return Response({
            'count': len(versiones),
            'results': versiones
        })

    @action(detail=True, methods=['get'])
    def diagnosticos(self, request, pk=None):
        """
        GET /api/pacientes/{id}/diagnosticos/
        Todos los diagnósticos del paciente
        """
        paciente = self.get_object()
        estado = request.query_params.get('estado')
        
        service = OdontogramaService()
        diagnosticos = service.obtener_diagnosticos_paciente(str(paciente.id), estado)
        
        serializer = DiagnosticoDentalListSerializer(diagnosticos, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='odontograma-fhir')
    def odontograma_fhir(self, request, pk=None):
        """
        GET /api/pacientes/{id}/odontograma-fhir/
        Retorna el odontograma completo como Bundle FHIR
        """
        paciente = self.get_object()
        serializer = FHIRBundleSerializer(paciente)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DienteViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar dientes de pacientes"""
    permission_classes = [IsAuthenticated]
    serializer_class = DienteDetailSerializer

    def get_queryset(self):
        paciente_id = self.request.query_params.get('paciente_id')
        if paciente_id:
            return Diente.objects.filter(
                paciente_id=paciente_id
            ).prefetch_related('superficies__diagnosticos')
        
        return Diente.objects.all().prefetch_related('superficies__diagnosticos')

    @action(detail=True, methods=['post'])
    def marcar_ausente(self, request, pk=None):
        """
        POST /api/dientes/{id}/marcar_ausente/
        """
        diente = self.get_object()
        service = OdontogramaService()
        
        odontologo_id = request.data.get('odontologo_id', request.user.id)
        diente = service.marcar_diente_ausente(
            str(diente.paciente.id),
            diente.codigo_fdi,
            odontologo_id
        )
        
        serializer = self.get_serializer(diente)
        return Response(serializer.data)
    
    
    

class SuperficieDentalViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consultar superficies dentales"""
    serializer_class = SuperficieDentalListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        diente_id = self.request.query_params.get('diente_id')
        if diente_id:
            return SuperficieDental.objects.filter(
                diente_id=diente_id
            ).prefetch_related('diagnosticos')
        
        return SuperficieDental.objects.all()


class DiagnosticoDentalViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar diagnósticos dentales aplicados"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = DiagnosticoDental.objects.all()
        
        # Filtros
        sesion_id = self.request.query_params.get('sesion_id')
        paciente_id = self.request.query_params.get('paciente_id')
        numero_diente = self.request.query_params.get('numero_diente')
        estado = self.request.query_params.get('estado')
        
        if sesion_id:
            queryset = queryset.filter(superficie__diente__paciente_id=sesion_id)
        if paciente_id:
            queryset = queryset.filter(superficie__diente__paciente_id=paciente_id)
        if numero_diente:
            queryset = queryset.filter(superficie__diente__codigo_fdi=numero_diente)
        if estado:
            queryset = queryset.filter(estado_tratamiento=estado)
        
        return queryset.select_related(
            'diagnostico_catalogo',
            'superficie',
            'odontologo'
        ).prefetch_related('superficie__diente')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DiagnosticoDentalCreateSerializer
        elif self.action == 'retrieve':
            return DiagnosticoDentalDetailSerializer
        return DiagnosticoDentalListSerializer

    @action(detail=True, methods=['post'])
    def marcar_tratado(self, request, pk=None):
        """
        POST /api/diagnosticos-aplicados/{id}/marcar_tratado/
        """
        service = OdontogramaService()
        diagnostico = service.marcar_diagnostico_tratado(
            diagnostico_id=str(pk),
            odontologo_id=request.user.id,
        )
        serializer = self.get_serializer(diagnostico)
        return Response(serializer.data)
    
    
    @action(detail=True, methods=['delete'])
    def eliminar(self, request, pk=None):
        """
        DELETE /api/diagnosticos-aplicados/{id}/eliminar/
        
        Soporta dos modos:
        1. Individual: DELETE /api/diagnosticos-aplicados/{id}/eliminar/
        2. Batch: DELETE /api/diagnosticos-aplicados/{cualquier-id}/eliminar/
        con body: {"diagnostico_ids": ["uuid1", "uuid2", ...]}
        """
        service = OdontogramaService()
        odontologo_id = request.user.id
        
        # Verificar si hay múltiples IDs en el body (modo BATCH)
        diagnostico_ids = request.data.get('diagnostico_ids', [])
        
        if diagnostico_ids and len(diagnostico_ids) > 0:
            # ========== MODO BATCH ==========
            logger.info(f"[eliminar] Modo BATCH: {len(diagnostico_ids)} diagnósticos")
            
            try:
                resultado = service.eliminardiagnosticosbatch( 
                    diagnosticoids=diagnostico_ids,   
                    odontologoid=odontologo_id   
                )
                
                if not resultado.get('success'):
                    return Response({
                        'success': False,
                        'error': resultado.get('error', 'Error al eliminar diagnósticos')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                return Response({
                    'success': True,
                    'eliminados': resultado['eliminados'],
                    'version_id': resultado['versionid'],
                    'descripcion': resultado['descripcion']
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                import traceback
                logger.error(f"[eliminar] Error batch: {str(e)}")
                logger.error(traceback.format_exc())
                
                return Response({
                    'success': False,
                    'error': f'Error interno: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            # ========== MODO INDIVIDUAL ==========
            logger.info(f"[eliminar] Modo INDIVIDUAL: {pk}")
            
            try:
                diagnostico = self.get_object()
                resultado = service.eliminar_diagnostico(
                    str(diagnostico.id), 
                    odontologo_id
                )
                
                if resultado:
                    return Response({
                        'success': True
                    }, status=status.HTTP_200_OK)
                
                return Response({
                    'success': False,
                    'error': 'No se pudo eliminar'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            except Exception as e:
                import traceback
                logger.error(f"[eliminar] Error individual: {str(e)}")
                logger.error(traceback.format_exc())
                
                return Response({
                    'success': False,
                    'error': f'Error interno: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# ===== CLASES DE PAGINACIÓN =====

class HistorialPagination(PageNumberPagination):
    """Paginación estándar para historial general"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
    
class HistorialCursorPagination(CursorPagination):
    """Paginación cursor para timeline/infinite scroll"""
    page_size = 20
    ordering = '-fecha'
    cursor_query_param = 'cursor'
    

class HistorialOdontogramaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar historial del odontograma
    Optimizado con caché y prefetch
    """
    serializer_class = HistorialOdontogramaSerializer
    permission_classes = [IsAuthenticated, UserBasedPermission]
    permission_model_name = "historialodontograma"
    pagination_class = HistorialPagination
    
    def get_queryset(self):
        """Queryset optimizado con select_related y prefetch_related"""
        diente_id = self.request.query_params.get('diente_id')
        paciente_id = self.request.query_params.get('paciente_id')
        odontologo_id = self.request.query_params.get('odontologo_id')
        version_id = self.request.query_params.get('version_id')
        
        if version_id:
            self.pagination_class = None
        
        queryset = HistorialOdontograma.objects.select_related(
            'odontologo',
            'diente',
            'diente__paciente'  
        ).order_by('-fecha', '-version_id', '-id')
        
        if version_id:
            queryset = queryset.filter(version_id=version_id)
        elif diente_id:
            queryset = queryset.filter(diente_id=diente_id)
        elif paciente_id:
            queryset = queryset.filter(diente__paciente_id=paciente_id)
        elif odontologo_id:
            queryset = queryset.filter(odontologo_id=odontologo_id)
        
        return queryset
    
class HistorialCursorPagination(CursorPagination):
    page_size = 20
    ordering = '-fecha'  # Más reciente primero
    cursor_query_param = 'cursor'

class OdontogramaCompletoView(APIView):
    """
    Devuelve el odontograma completo del paciente (ultimo guardado)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, paciente_id):
        try:
            paciente = Paciente.objects.get(id=paciente_id)
        except Paciente.DoesNotExist:
            return Response(
                {"detail": "Paciente no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        service = OdontogramaService()
        odontograma_dict = service.obtener_odontograma_completo(paciente_id)

        odontograma_completo_backend  = {
            "paciente": {
                "id": str(paciente.id),
                "nombres": paciente.nombres,
                "apellidos": paciente.apellidos,
                "cedula_pasaporte": paciente.cedula_pasaporte,
            },
            "odontograma_data": odontograma_dict["odontograma_data"],
            "fecha_obtension": odontograma_dict["fecha_obtension"],
        }

        return Response(odontograma_completo_backend, status=status.HTTP_200_OK)


@api_view(['GET'])
def obtener_definiciones_superficies(request):
    """
    GET /api/odontograma/definiciones-superficies/
    Retorna el mapeo de IDs de frontend a backend para superficies dentales
    """
    definiciones = []
    
    for id_frontend, id_backend in SuperficieDental.FRONTEND_ID_TO_BACKEND.items():
        # Obtener nombre legible desde choices
        nombre_display = dict(SuperficieDental.TipoSuperficie.choices).get(
            id_backend, 
            id_backend.replace('_', ' ').title()
        )
        
        # Obtener área anatómica
        area = SuperficieDental.SUPERFICIE_A_AREA.get(id_backend, 'general')
        
        # Obtener código FHIR
        fhir_info = SuperficieDental.FHIR_SURFACE_MAPPING.get(id_backend, (None, None))
        codigo_fhir = fhir_info[0] if fhir_info else None
        
        definiciones.append({
            'id_frontend': id_frontend,
            'id_backend': id_backend,
            'nombre': nombre_display,
            'area': area,
            'codigo_fhir': codigo_fhir,
        })
    
    return Response({
        'definiciones': definiciones,
        'total': len(definiciones),
    }, status=status.HTTP_200_OK)
    
    
    # Guardar odontograma completo
@api_view(['POST'])
def guardar_odontograma_completo(request, paciente_id):
    """
    POST /api/odontogram/pacientes/{paciente_id}/guardar-odontograma/
    Guarda el odontograma completo con todos los diagnósticos
    """
    service = OdontogramaService()
    odontologo_id = request.data.get('odontologo_id', request.user.id)
    odontograma_data = request.data.get('odontograma_data', {})
    
    resultado = service.guardar_odontograma_completo(
        paciente_id=paciente_id,
        odontograma_data=odontograma_data,
        odontologo_id=odontologo_id
    )
    return Response(resultado, status=status.HTTP_200_OK)
class IndicadoresSaludBucalPagination(PageNumberPagination):
    """
    Paginación para indicadores de salud bucal.
    10 registros por página es razonable para este tipo de datos.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
    
    
class IndicadoresSaludBucalViewSet(viewsets.ModelViewSet):
    """
    CRUD de Indicadores de Salud Bucal por paciente.
    Implementa borrado lógico usando el campo 'activo'.
    """
    serializer_class = IndicadoresSaludBucalSerializer
    permission_classes = [IsAuthenticated]
    permission_model_name = 'indicadores_salud_bucal'
    pagination_class = IndicadoresSaludBucalPagination

    def get_queryset(self):
        paciente_id = self.request.query_params.get('paciente_id')
        incluir_inactivos = self.request.query_params.get('incluir_inactivos', 'false').lower() == 'true'
        
        logger.info(f"[IndicadoresSaludBucalViewSet] GET queryset")
        logger.info(f" → paciente_id: {paciente_id}")
        logger.info(f" → incluir_inactivos: {incluir_inactivos}")

        # Usar el manager apropiado
        if incluir_inactivos:
            qs = IndicadoresSaludBucal.all_objects.select_related(
                'paciente', 'creado_por', 'actualizado_por', 'eliminado_por'
            ).all()
        else:
            qs = IndicadoresSaludBucal.objects.select_related(
                'paciente', 'creado_por', 'actualizado_por'
            ).all()

        if paciente_id:
            qs = qs.filter(paciente_id=paciente_id)
            count = qs.count()
            logger.info(f" → Registros encontrados: {count}")
        else:
            logger.warning(" → ⚠️ NO se proporcionó paciente_id")

        return qs.order_by('-fecha')

    def perform_create(self, serializer):
        logger.info(f"[IndicadoresSaludBucalViewSet] CREATE")
        logger.info(f" → Usuario: {self.request.user}")
        
        # Asignar creado_por automáticamente
        indicadores = serializer.save(
            creado_por=self.request.user,
            activo=True
        )
        IndicadoresSaludBucalService.calcular_promedios(indicadores)
        
        logger.info(f" → Indicador creado: {indicadores.id}")

    def perform_update(self, serializer):
        logger.info(f"[IndicadoresSaludBucalViewSet] UPDATE")
        logger.info(f" → Usuario: {self.request.user}")
        
        # Asignar actualizado_por automáticamente
        indicadores = serializer.save(actualizado_por=self.request.user)
        IndicadoresSaludBucalService.calcular_promedios(indicadores)
        
        logger.info(f" → Indicador actualizado: {indicadores.id}")

    def perform_destroy(self, instance):
        """
        Override destroy para implementar borrado lógico.
        No elimina físicamente el registro, solo marca activo=False.
        """
        logger.info(f"[IndicadoresSaludBucalViewSet] DELETE (lógico)")
        logger.info(f" → Indicador: {instance.id}")
        logger.info(f" → Usuario: {self.request.user}")
        
        # Borrado lógico
        instance.activo = False
        instance.eliminado_por = self.request.user
        instance.fecha_eliminacion = timezone.now()
        instance.save()
        
        logger.info(f" → Indicador marcado como inactivo")
    
    @action(detail=True, methods=['post'], url_path='restaurar')
    def restaurar(self, request, pk=None):
        """
        POST /api/indicadores-salud-bucal/{id}/restaurar/
        Restaura un indicador eliminado lógicamente.
        """
        logger.info(f"[IndicadoresSaludBucalViewSet] RESTAURAR")
        logger.info(f" → Indicador: {pk}")
        logger.info(f" → Usuario: {request.user}")
        
        # Obtener el indicador (incluyendo inactivos)
        indicador = IndicadoresSaludBucal.all_objects.get(pk=pk)
        
        if indicador.activo:
            return Response(
                {"error": "Este indicador ya está activo"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Restaurar
        indicador.activo = True
        indicador.eliminado_por = None
        indicador.fecha_eliminacion = None
        indicador.actualizado_por = request.user
        indicador.save()
        
        logger.info(f" → Indicador restaurado exitosamente")
        
        serializer = self.get_serializer(indicador)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='eliminados')
    def eliminados(self, request):
        """
        GET /api/indicadores-salud-bucal/eliminados/?paciente_id=...
        Lista todos los indicadores eliminados lógicamente.
        """
        paciente_id = request.query_params.get('paciente_id')
        
        logger.info(f"[IndicadoresSaludBucalViewSet] ELIMINADOS")
        logger.info(f" → paciente_id: {paciente_id}")
        
        queryset = IndicadoresSaludBucal.all_objects.filter(activo=False)
        
        if paciente_id:
            queryset = queryset.filter(paciente_id=paciente_id)
        
        queryset = queryset.select_related(
            'paciente', 'creado_por', 'eliminado_por'
        ).order_by('-fecha_eliminacion')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
class IndicadoresSaludBucalListView(generics.ListAPIView):
    serializer_class = IndicadoresSaludBucalSerializer

    def get_queryset(self):
        paciente_id = self.kwargs.get("paciente_id")
        search = self.request.query_params.get("search", "").strip()

        qs = IndicadoresSaludBucal.objects.filter(paciente_id=paciente_id)

        if search:
            qs = qs.filter(
                Q(paciente__nombres__icontains=search) |
                Q(paciente__apellidos__icontains=search) |
                Q(paciente__cedulapasaporte__icontains=search) |
                Q(enfermedad_periodontal__icontains=search) |
                Q(tipo_oclusion__icontains=search) |
                Q(nivel_fluorosis__icontains=search) |
                Q(fecha__icontains=search)
            )

        return qs.order_by("-fecha")