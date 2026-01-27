# api/appointment/views.py

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from datetime import datetime, timedelta
from django.utils import timezone

from .services.appointment_service import RecordatorioService

from .models import Cita, EstadoCita, HorarioAtencion, RecordatorioCita
from .serializers import (
    CitaSerializer, CitaDetailSerializer, CitaCreateSerializer,
    CitaUpdateSerializer, CitaCancelarSerializer, CitaReprogramarSerializer,
    CitaEstadoSerializer, HorariosDisponiblesSerializer,
    HorarioAtencionSerializer, RecordatorioCitaSerializer, RecordatorioEnvioSerializer
)
from .services import CitaService, HorarioAtencionService
from api.users.permissions import UserBasedPermission
import logging

logger = logging.getLogger(__name__)

class CitaPagination(PageNumberPagination):
    """Configuración de paginación para citas"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class CitaViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de citas"""
    queryset = Cita.objects.all()
    permission_classes = [IsAuthenticated, UserBasedPermission]
    permission_model_name = "agenda"
    pagination_class = CitaPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['odontologo', 'paciente', 'fecha', 'estado', 'tipo_consulta', 'activo']
    ordering_fields = ['fecha', 'hora_inicio', 'fecha_creacion']
    ordering = ['-fecha', '-hora_inicio']
    
    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción"""
        if self.action == 'create':
            return CitaCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CitaUpdateSerializer
        elif self.action == 'retrieve':
            return CitaDetailSerializer
        return CitaSerializer
    
    def get_queryset(self):
        """Queryset base con filtros y búsqueda"""
        request = self.request
        search = (request.query_params.get("search") or "").strip()
        activo_param = request.query_params.get("activo")
        fecha_inicio = request.query_params.get("fecha_inicio")
        fecha_fin = request.query_params.get("fecha_fin")
        
        qs = Cita.objects.select_related(
            'paciente', 'odontologo', 'creado_por'
        ).order_by('-fecha', '-hora_inicio')
        
        if activo_param is not None:
            activo = activo_param.lower() == 'true'
            qs = qs.filter(activo=activo)
        else:
            qs = qs.filter(activo=True)
        
        if fecha_inicio and fecha_fin:
            qs = qs.filter(fecha__range=[fecha_inicio, fecha_fin])
        
        if search:
            qs = qs.filter(
                Q(paciente__nombres__icontains=search) |
                Q(paciente__apellidos__icontains=search) |
                Q(paciente__cedula_pasaporte__icontains=search) |
                Q(odontologo__nombres__icontains=search) |
                Q(odontologo__apellidos__icontains=search) |
                Q(motivo_consulta__icontains=search)
            )
        
        return qs
    
    def create(self, request, *args, **kwargs):
        """Crear nueva cita"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            cita = CitaService.crear_cita(serializer.validated_data)
            output_serializer = CitaDetailSerializer(cita)
            logger.info(f"Cita creada para paciente {cita.paciente.nombre_completo} por {request.user.username}")
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            logger.error(f"Error creando cita: {str(e)}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """Actualizar cita"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            cita = CitaService.actualizar_cita(instance.id, serializer.validated_data)
            output_serializer = CitaDetailSerializer(cita)
            logger.info(f"Cita {cita.id} actualizada por {request.user.username}")
            return Response(output_serializer.data)
        except ValidationError as e:
            logger.error(f"Error actualizando cita: {str(e)}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminación lógica de la cita"""
        instance = self.get_object()
        CitaService.eliminar_cita(instance.id)
        logger.info(f"Cita {instance.id} eliminada por {request.user.username}")
        return Response({'id': str(instance.id)}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='del-dia')
    def citas_del_dia(self, request):
        """
        RF-05.16: Dashboard de citas del día actual al ingresar al módulo,
        con lista cronológica de pacientes programados
        GET /api/appointments/citas/del-dia/
        GET /api/appointments/citas/del-dia/?odontologo=uuid
        """
        from datetime import date
        
        hoy = date.today()
        odontologo_id = request.query_params.get('odontologo')
        
        # Filtro base: solo citas del día activas
        citas_query = Cita.objects.filter(
            fecha=hoy,
            activo=True
        ).exclude(
            estado__in=[EstadoCita.CANCELADA, EstadoCita.REPROGRAMADA]
        ).select_related('paciente', 'odontologo').order_by('hora_inicio')
        
        # Filtro opcional por odontólogo
        if odontologo_id:
            citas_query = citas_query.filter(odontologo_id=odontologo_id)
        
        serializer = self.get_serializer(citas_query, many=True)
        
        # Estadísticas del día
        total = citas_query.count()
        completadas = citas_query.filter(estado=EstadoCita.ASISTIDA).count()
        pendientes = citas_query.filter(
            estado__in=[EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA]
        ).count()
        en_proceso = citas_query.filter(estado=EstadoCita.EN_ATENCION).count()
        no_asistieron = citas_query.filter(estado=EstadoCita.NO_ASISTIDA).count()
        
        # Siguiente cita (la más próxima pendiente)
        from django.utils import timezone
        ahora = timezone.localtime(timezone.now()).time()
        siguiente_cita = citas_query.filter(
            hora_inicio__gte=ahora,
            estado__in=[EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA]
        ).first()
        
        return Response({
            'fecha': hoy.strftime('%Y-%m-%d'),
            'fecha_display': hoy.strftime('%d de %B de %Y'),
            'total_citas': total,
            'citas': serializer.data,
            'estadisticas': {
                'total': total,
                'completadas': completadas,
                'pendientes': pendientes,
                'en_proceso': en_proceso,
                'no_asistieron': no_asistieron,
                'tasa_asistencia': round((completadas / total * 100), 2) if total > 0 else 0
            },
            'siguiente_cita': CitaSerializer(siguiente_cita).data if siguiente_cita else None
        })
        

    @action(detail=True, methods=['get'], url_path='historial')
    def historial(self, request, pk=None):
        """
        RF-05.11: Obtiene el historial de cambios de una cita
        GET /api/appointments/citas/{id}/historial/
        """
        from .models import HistorialCita
        from .serializers import HistorialCitaSerializer
        
        cita = self.get_object()
        historial = HistorialCita.objects.filter(cita=cita).select_related('usuario')
        serializer = HistorialCitaSerializer(historial, many=True)
        
        return Response({
            'cita_id': str(cita.id),
            'paciente': cita.paciente.nombre_completo,
            'total_cambios': historial.count(),
            'historial': serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        """Cancelar una cita"""
        serializer = CitaCancelarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            cita = CitaService.cancelar_cita(
                pk,
                serializer.validated_data['motivo_cancelacion'],
                request.user
            )
            output_serializer = CitaDetailSerializer(cita)
            logger.info(f"Cita {pk} cancelada por {request.user.username}")
            return Response(output_serializer.data)
        except ValidationError as e:
            # ✅ CORRECCIÓN: Devolver error 400 en lugar de 500
            logger.warning(f"Error cancelando cita {pk}: {str(e)} - Usuario: {request.user.username}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

    @action(detail=True, methods=['post'], url_path='reprogramar')
    def reprogramar(self, request, pk=None):
        """Reprogramar una cita"""
        serializer = CitaReprogramarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Obtener la cita original antes de reprogramar
            cita_original = self.get_object()
            
            # Log de información original
            logger.info(
                f"Iniciando reprogramación - Cita ID: {pk}, "
                f"Fecha original: {cita_original.fecha} {cita_original.hora_inicio}, "
                f"Estado original: {cita_original.estado}"
            )
            
            # Reprogramar la cita
            nueva_cita = CitaService.reprogramar_cita(
                pk,
                serializer.validated_data['nueva_fecha'],
                serializer.validated_data['nueva_hora_inicio'],
                request.user
            )
            
            # ✅ Verificar que el estado sea REPROGRAMADA
            if nueva_cita.estado != EstadoCita.REPROGRAMADA:
                logger.warning(f"Cita reprogramada con estado incorrecto: {nueva_cita.estado}")
                # Forzar el estado correcto
                nueva_cita.estado = EstadoCita.REPROGRAMADA
                nueva_cita.save()
            
            output_serializer = CitaDetailSerializer(nueva_cita)
            
            # Log detallado del resultado
            logger.info(
                f"Cita reprogramada exitosamente. "
                f"Nueva cita ID: {nueva_cita.id}, "
                f"Nueva fecha: {nueva_cita.fecha} {nueva_cita.hora_inicio}, "
                f"Estado: {nueva_cita.estado}, "
                f"Usuario: {request.user.username}"
            )
            
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            logger.error(f"Error reprogramando cita {pk}: {str(e)}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        """Cambiar estado de una cita"""
        serializer = CitaEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            cita = CitaService.cambiar_estado_cita(
                pk,
                serializer.validated_data['estado']
            )
            output_serializer = CitaDetailSerializer(cita)
            logger.info(f"Estado de cita {pk} cambiado a {serializer.validated_data['estado']} por {request.user.username}")
            return Response(output_serializer.data)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

    @action(detail=True, methods=["post"], url_path="recordatorio")
    def enviar_recordatorio(self, request, pk=None) -> Response:
        """POST /api/appointments/citas/{id}/recordatorio/"""
        serializer = RecordatorioEnvioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            tipo_recordatorio = serializer.validated_data.get('tipo_recordatorio', 'EMAIL')
            destinatario = serializer.validated_data.get('destinatario', 'PACIENTE')
            mensaje = serializer.validated_data.get('mensaje', '')
            
            resultado = RecordatorioService.enviar_recordatorio_manual(
                pk, 
                tipo_recordatorio=tipo_recordatorio,
                destinatario=destinatario,
                mensaje=mensaje
            )
            
            return Response(resultado, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error recordatorio cita {pk}: {str(e)}")
            return Response({"error": "Error interno"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    
    

    @action(detail=False, methods=['get'], url_path='proximas')
    def citas_proximas(self, request):
        """
        RF-05.17: Genera alertas visuales de citas próximas 
        (dentro de los siguientes 30 minutos) en el dashboard principal
        GET /api/appointments/citas/proximas/
        GET /api/appointments/citas/proximas/?minutos=30
        """
        from datetime import datetime, timedelta, date
        from django.utils import timezone
        
        # Parámetro configurable (por defecto 30 minutos)
        minutos_ventana = int(request.query_params.get('minutos', 30))
        
        ahora = timezone.localtime(timezone.now())
        hoy = date.today()
        limite_superior = ahora + timedelta(minutes=minutos_ventana)
        
        logger.info(f"🔍 Buscando citas próximas. Hora actual: {ahora}, Límite: {limite_superior}")
        
        # Buscar citas del día actual pendientes
        citas = Cita.objects.filter(
            fecha=hoy,
            activo=True,
            estado__in=[EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA]
        ).select_related('paciente', 'odontologo').order_by('hora_inicio')
        
        citas_proximas = []
        
        for cita in citas:
            fecha_hora_cita = timezone.make_aware(
                datetime.combine(cita.fecha, cita.hora_inicio)
            )
            
            # Solo citas futuras dentro de la ventana de tiempo
            if ahora <= fecha_hora_cita <= limite_superior:
                minutos_faltantes = int((fecha_hora_cita - ahora).total_seconds() / 60)
                
                # Determinar nivel de alerta
                if minutos_faltantes <= 5:
                    nivel_alerta = 'CRITICA'  # Rojo intenso
                    color_alerta = '#DC2626'
                elif minutos_faltantes <= 15:
                    nivel_alerta = 'ALTA'  # Naranja
                    color_alerta = '#F59E0B'
                else:
                    nivel_alerta = 'MEDIA'  # Amarillo
                    color_alerta = '#EAB308'
                
                citas_proximas.append({
                    'id': str(cita.id),
                    'fecha': cita.fecha.strftime('%Y-%m-%d'),
                    'hora_inicio': cita.hora_inicio.strftime('%H:%M'),
                    'hora_fin': cita.hora_fin.strftime('%H:%M'),
                    'minutos_faltantes': minutos_faltantes,
                    'nivel_alerta': nivel_alerta,
                    'color_alerta': color_alerta,
                    'paciente': {
                        'id': str(cita.paciente.id),
                        'nombre_completo': cita.paciente.nombre_completo,
                        'telefono': cita.paciente.telefono or '',
                        'correo': cita.paciente.correo or '',
                    },
                    'odontologo': {
                        'id': str(cita.odontologo.id),
                        'nombre_completo': cita.odontologo.get_full_name(),
                    },
                    'tipo_consulta': cita.tipo_consulta,
                    'tipo_consulta_display': cita.get_tipo_consulta_display(),
                    'motivo_consulta': cita.motivo_consulta or '',
                    'duracion': cita.duracion,
                    'estado': cita.estado,
                    'estado_display': cita.get_estado_display(),
                })
        
        logger.info(f"✅ Encontradas {len(citas_proximas)} citas próximas")
        
        return Response({
            'total_alertas': len(citas_proximas),
            'hora_actual': ahora.strftime('%H:%M'),
            'fecha_actual': hoy.strftime('%Y-%m-%d'),
            'ventana_minutos': minutos_ventana,
            'citas_proximas': citas_proximas,
            'tiene_alertas_criticas': any(c['nivel_alerta'] == 'CRITICA' for c in citas_proximas)
        })




    @action(detail=False, methods=['get'], url_path='estadisticas-recordatorios')
    def estadisticas_recordatorios(self, request):
        """GET /api/appointments/citas/estadisticas-recordatorios/"""
        try:
            from datetime import datetime, timedelta
            
            # Calcular estadísticas básicas
            ultimos_30_dias = datetime.now() - timedelta(days=30)
            
            total_recordatorios = RecordatorioCita.objects.count()
            exitosos = RecordatorioCita.objects.filter(enviado_exitosamente=True).count()
            fallidos = RecordatorioCita.objects.filter(enviado_exitosamente=False).count()
            
            # Por destinatario
            por_destinatario = {
                'PACIENTE': RecordatorioCita.objects.filter(destinatario='PACIENTE').count(),
                'ODONTOLOGO': RecordatorioCita.objects.filter(destinatario='ODONTOLOGO').count(),
                'AMBOS': RecordatorioCita.objects.filter(destinatario='AMBOS').count(),
            }
            
            # Últimos recordatorios
            ultimos = RecordatorioCita.objects.select_related(
                'cita', 'cita__paciente', 'cita__odontologo'
            ).order_by('-fecha_envio')[:10]
            
            datos = {
                'total_enviados': total_recordatorios,
                'exitosos': exitosos,
                'fallidos': fallidos,
                'tasa_exito': (exitosos / total_recordatorios * 100) if total_recordatorios > 0 else 0,
                'por_destinatario': por_destinatario,
                'ultimos_recordatorios': RecordatorioCitaSerializer(ultimos, many=True).data
            }
            
            return Response(datos)
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return Response(
                {'error': 'Error al obtener estadísticas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




    
    @action(detail=False, methods=['get'], url_path='por-odontologo/(?P<odontologo_id>[^/.]+)')
    def por_odontologo(self, request, odontologo_id=None):
        """Obtener citas de un odontólogo"""
        fecha = request.query_params.get('fecha')
        if not fecha:
            return Response(
                {'detail': 'El parámetro fecha es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            citas = CitaService.obtener_citas_por_fecha_y_odontologo(fecha_obj, odontologo_id)
            citas = citas.filter(activo=True)
            serializer = self.get_serializer(citas, many=True)
            return Response(serializer.data)
        except ValueError:
            return Response(
                {'detail': 'Formato de fecha inválido. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], url_path='por-semana')
    def por_semana(self, request):
        """Obtener citas de una semana"""
        fecha_inicio = request.query_params.get('fecha_inicio')
        odontologo_id = request.query_params.get('odontologo')
        
        if not fecha_inicio:
            return Response(
                {'detail': 'El parámetro fecha_inicio es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            fecha_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            citas = CitaService.obtener_citas_por_semana(fecha_obj, odontologo_id)
            citas = citas.filter(activo=True)
            serializer = self.get_serializer(citas, many=True)
            return Response(serializer.data)
        except ValueError:
            return Response(
                {'detail': 'Formato de fecha inválido. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
    

    @action(detail=False, methods=['post'], url_path='horarios-disponibles')
    def horarios_disponibles(self, request):
        """Obtener horarios disponibles para un odontólogo en una fecha"""
        serializer = HorariosDisponiblesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        horarios = CitaService.obtener_horarios_disponibles(
            serializer.validated_data['odontologo'],
            serializer.validated_data['fecha'],
            serializer.validated_data.get('duracion', 30)
        )
        
        return Response({'horarios_disponibles': horarios})
    
    @action(detail=False, methods=['get'], url_path='by-paciente/(?P<paciente_id>[^/.]+)')
    def by_paciente(self, request, paciente_id=None):
        """Obtener citas de un paciente"""
        try:
            citas = Cita.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).order_by('-fecha', '-hora_inicio')
            serializer = self.get_serializer(citas, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'detail': 'No se encontraron citas para este paciente'},
                status=status.HTTP_404_NOT_FOUND
            )

class HorarioAtencionViewSet(viewsets.ModelViewSet):
    """ViewSet para horarios de atención"""
    serializer_class = HorarioAtencionSerializer
    queryset = HorarioAtencion.objects.all()
    permission_classes = [IsAuthenticated, UserBasedPermission]
    permission_model_name = "agenda"
    pagination_class = CitaPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['odontologo', 'dia_semana', 'activo']
    ordering_fields = ['dia_semana', 'hora_inicio']
    ordering = ['dia_semana', 'hora_inicio']
    
    def get_queryset(self):
        """Queryset base"""
        activo_param = self.request.query_params.get("activo")
        qs = HorarioAtencion.objects.select_related('odontologo').order_by('dia_semana', 'hora_inicio')
        
        if activo_param is not None:
            activo = activo_param.lower() == 'true'
            qs = qs.filter(activo=activo)
        
        return qs
    
    def create(self, request, *args, **kwargs):
        """Crear horario de atención"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        logger.info(f"Horario de atención creado por {request.user.username}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """✅ Actualizar horario - Con mejor manejo de errores"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        try:
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            logger.info(f"Horario {instance.id} actualizado por {request.user.username}")
            return Response(serializer.data)
        except ValidationError as e:
            logger.error(f"Error actualizando horario: {str(e)}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error inesperado actualizando horario: {str(e)}")
            return Response({'detail': 'Error interno del servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def partial_update(self, request, *args, **kwargs):
        """✅ Actualización parcial (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminación lógica"""
        instance = self.get_object()
        instance.activo = False
        instance.save()
        logger.info(f"Horario {instance.id} desactivado por {request.user.username}")
        return Response({'id': str(instance.id)}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='por-odontologo/(?P<odontologo_id>[^/.]+)')
    def por_odontologo(self, request, odontologo_id=None):
        """Obtener horarios de un odontólogo"""
        horarios = HorarioAtencionService.obtener_horarios_por_odontologo(odontologo_id)
        serializer = self.get_serializer(horarios, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='horarios-disponibles')
    def horarios_disponibles(self, request):
        """Obtener horarios disponibles para un odontólogo en una fecha"""
        serializer = HorariosDisponiblesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        horarios = CitaService.obtener_horarios_disponibles(
            serializer.validated_data['odontologo'],
            serializer.validated_data['fecha'],
            serializer.validated_data.get('duracion', 30)
        )
        
        return Response({'horarios_disponibles': horarios})

class RecordatorioCitaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para ver recordatorios (solo lectura)"""
    serializer_class = RecordatorioCitaSerializer
    queryset = RecordatorioCita.objects.all()
    permission_classes = [IsAuthenticated, UserBasedPermission]
    permission_model_name = "agenda"
    pagination_class = CitaPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['cita', 'tipo_recordatorio', 'enviado_exitosamente']
    ordering = ['-fecha_envio']

