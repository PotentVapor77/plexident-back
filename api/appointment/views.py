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


# =============================================================================
# HELPER: Determina si el usuario tiene visibilidad total de citas
# =============================================================================

def _usuario_ve_todas_las_citas(user) -> bool:
    """
    Administrador y Asistente ven TODAS las citas.
    Odontólogo solo ve las suyas propias.
    """
    return getattr(user, 'rol', None) in ('Administrador', 'Asistente')


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

    # =========================================================================
    # QUERYSET CON FILTRO POR ROL
    # =========================================================================

    def get_queryset(self):
        """
        - Administrador / Asistente → todas las citas activas.
        - Odontólogo               → solo sus propias citas.
        Aplica además los filtros de búsqueda y rango de fechas.
        """
        request = self.request
        search = (request.query_params.get("search") or "").strip()
        activo_param = request.query_params.get("activo")
        fecha_inicio = request.query_params.get("fecha_inicio")
        fecha_fin = request.query_params.get("fecha_fin")

        qs = Cita.objects.select_related(
            'paciente', 'odontologo', 'creado_por'
        ).order_by('-fecha', '-hora_inicio')

        # ---- Filtro por activo ----
        if activo_param is not None:
            activo = activo_param.lower() == 'true'
            qs = qs.filter(activo=activo)
        else:
            qs = qs.filter(activo=True)

        # ---- Filtro por rol: Odontólogo solo ve las suyas ----
        if not _usuario_ve_todas_las_citas(request.user):
            qs = qs.filter(odontologo=request.user)
            logger.debug(
                f"Odontólogo '{request.user.username}' consultando solo sus citas"
            )

        # ---- Filtro por rango de fechas ----
        if fecha_inicio and fecha_fin:
            qs = qs.filter(fecha__range=[fecha_inicio, fecha_fin])

        # ---- Búsqueda textual ----
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

    # =========================================================================
    # CRUD ESTÁNDAR
    # =========================================================================

    def create(self, request, *args, **kwargs):
        """Crear nueva cita"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cita = CitaService.crear_cita(serializer.validated_data)
            output_serializer = CitaDetailSerializer(cita)
            logger.info(
                f"Cita creada para paciente {cita.paciente.nombre_completo} "
                f"por {request.user.username}"
            )
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

    # =========================================================================
    # ACTIONS PERSONALIZADAS
    # =========================================================================

    def _aplicar_filtro_rol(self, qs, user, odontologo_id_param: str | None = None):
        """
        Aplica el filtro de visibilidad por rol a cualquier queryset de citas.

        - Administrador/Asistente: respetan el parámetro odontologo_id si viene,
          o devuelven todo si no viene.
        - Odontólogo: ignora odontologo_id_param y filtra siempre por sí mismo.
        """
        if _usuario_ve_todas_las_citas(user):
            if odontologo_id_param:
                qs = qs.filter(odontologo_id=odontologo_id_param)
        else:
            # Odontólogo: siempre solo sus citas, ignorar cualquier parámetro externo
            qs = qs.filter(odontologo=user)
        return qs

    @action(detail=False, methods=['get'], url_path='del-dia')
    def citas_del_dia(self, request):
        """
        RF-05.16: Citas del día actual con estadísticas.
        - Administrador/Asistente: todas o filtradas por ?odontologo=uuid
        - Odontólogo: solo las suyas propias
        """
        from datetime import date

        hoy = date.today()
        odontologo_id = request.query_params.get('odontologo')

        citas_query = Cita.objects.filter(
            fecha=hoy,
            activo=True
        ).exclude(
            estado__in=[EstadoCita.CANCELADA, EstadoCita.REPROGRAMADA]
        ).select_related('paciente', 'odontologo').order_by('hora_inicio')

        citas_query = self._aplicar_filtro_rol(citas_query, request.user, odontologo_id)

        serializer = self.get_serializer(citas_query, many=True)

        total = citas_query.count()
        completadas = citas_query.filter(estado=EstadoCita.ASISTIDA).count()
        pendientes = citas_query.filter(
            estado__in=[EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA]
        ).count()
        en_proceso = citas_query.filter(estado=EstadoCita.EN_ATENCION).count()
        no_asistieron = citas_query.filter(estado=EstadoCita.NO_ASISTIDA).count()

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
            },
            'siguiente_cita': CitaSerializer(siguiente_cita).data if siguiente_cita else None,
            # Indica al frontend si el usuario ve citas propias o todas
            'scope': 'own' if not _usuario_ve_todas_las_citas(request.user) else 'all',
        })

    @action(detail=False, methods=['get'], url_path='proximas')
    def citas_proximas(self, request):
        """
        RF-05.17: Alertas de citas próximas.
        - Administrador/Asistente: todas
        - Odontólogo: solo las suyas
        """
        minutos = int(request.query_params.get('minutos', 30))
        ahora = timezone.now()
        limite = ahora + timedelta(minutes=minutos)

        citas_query = Cita.objects.filter(
            activo=True,
            estado__in=[EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA],
        ).select_related('paciente', 'odontologo').order_by('fecha', 'hora_inicio')

        citas_query = self._aplicar_filtro_rol(citas_query, request.user)

        citas_proximas = []
        for cita in citas_query:
            fecha_hora = timezone.make_aware(
                datetime.combine(cita.fecha, cita.hora_inicio)
            )
            if ahora <= fecha_hora <= limite:
                citas_proximas.append(cita)

        serializer = self.get_serializer(citas_proximas, many=True)
        return Response({
            'minutos': minutos,
            'total': len(citas_proximas),
            'citas': serializer.data,
            'scope': 'own' if not _usuario_ve_todas_las_citas(request.user) else 'all',
        })

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        """Cancelar una cita"""
        instance = self.get_object()
        serializer = CitaCancelarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cita = CitaService.cancelar_cita(
                instance.id,
                serializer.validated_data['motivo_cancelacion'],
                request.user
            )
            output_serializer = CitaDetailSerializer(cita)
            logger.info(f"Cita {instance.id} cancelada por {request.user.username}")
            return Response(output_serializer.data)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='reprogramar')
    def reprogramar(self, request, pk=None):
        """Reprogramar una cita"""
        instance = self.get_object()
        serializer = CitaReprogramarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            nueva_cita = CitaService.reprogramar_cita(
                instance.id,
                serializer.validated_data['nueva_fecha'],
                serializer.validated_data['nueva_hora_inicio'],
                serializer.validated_data.get('duracion', instance.duracion)
            )
            output_serializer = CitaDetailSerializer(nueva_cita)
            logger.info(f"Cita {instance.id} reprogramada por {request.user.username}")
            return Response(output_serializer.data)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        """Cambiar el estado de una cita"""
        instance = self.get_object()
        serializer = CitaEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cita = CitaService.cambiar_estado_cita(
                instance.id,
                serializer.validated_data['estado']
            )
            output_serializer = CitaDetailSerializer(cita)
            logger.info(
                f"Cita {instance.id}: estado cambiado a "
                f"{serializer.validated_data['estado']} por {request.user.username}"
            )
            return Response(output_serializer.data)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='historial')
    def historial(self, request, pk=None):
        """Obtener historial de cambios de una cita"""
        instance = self.get_object()
        from .models import HistorialCita
        from .serializers import HistorialCitaSerializer
        historial = HistorialCita.objects.filter(
            cita=instance
        ).select_related('usuario').order_by('-fecha_cambio')
        serializer = HistorialCitaSerializer(historial, many=True)
        return Response({
            'cita_id': str(instance.id),
            'total_cambios': historial.count(),
            'historial': serializer.data,
        })

    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request):
        """
        Estadísticas de citas.
        - Administrador/Asistente: estadísticas globales (o filtradas por ?odontologo=uuid)
        - Odontólogo: estadísticas solo de sus citas
        """
        try:
            odontologo_id = request.query_params.get('odontologo')

            qs = Cita.objects.filter(activo=True)
            qs = self._aplicar_filtro_rol(qs, request.user, odontologo_id)

            total = qs.count()
            por_estado = {}
            for estado in EstadoCita:
                por_estado[estado.value] = qs.filter(estado=estado).count()

            return Response({
                'total': total,
                'por_estado': por_estado,
                'scope': 'own' if not _usuario_ve_todas_las_citas(request.user) else 'all',
            })
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return Response(
                {'error': 'Error al obtener estadísticas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['get'],
        url_path='por-odontologo/(?P<odontologo_id>[^/.]+)'
    )
    def por_odontologo(self, request, odontologo_id=None):
        """
        Obtener citas de un odontólogo específico.
        - Administrador/Asistente: pueden ver las citas de cualquier odontólogo.
        - Odontólogo: solo puede ver sus propias citas (odontologo_id ignorado).
        """
        fecha = request.query_params.get('fecha')
        if not fecha:
            return Response(
                {'detail': 'El parámetro fecha es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()

            # Determinar qué odontólogo consultar
            odontologo_efectivo = (
                odontologo_id
                if _usuario_ve_todas_las_citas(request.user)
                else str(request.user.id)
            )

            citas = CitaService.obtener_citas_por_fecha_y_odontologo(
                fecha_obj, odontologo_efectivo
            )
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
        """
        Obtener citas de una semana.
        - Administrador/Asistente: todas o filtradas por ?odontologo=uuid
        - Odontólogo: solo las suyas, ignorando ?odontologo
        """
        fecha_inicio = request.query_params.get('fecha_inicio')
        odontologo_id = request.query_params.get('odontologo')

        if not fecha_inicio:
            return Response(
                {'detail': 'El parámetro fecha_inicio es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            fecha_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()

            # Determinar qué odontólogo usar para la consulta
            odontologo_efectivo = (
                odontologo_id
                if _usuario_ve_todas_las_citas(request.user)
                else str(request.user.id)
            )

            citas = CitaService.obtener_citas_por_semana(fecha_obj, odontologo_efectivo)
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

    @action(
        detail=False,
        methods=['get'],
        url_path='by-paciente/(?P<paciente_id>[^/.]+)'
    )
    def by_paciente(self, request, paciente_id=None):
        """
        Obtener citas de un paciente.
        - Administrador/Asistente: todas las citas del paciente.
        - Odontólogo: solo las citas de ese paciente que él atendió/atenderá.
        """
        try:
            qs = Cita.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).order_by('-fecha', '-hora_inicio')

            qs = self._aplicar_filtro_rol(qs, request.user)

            serializer = self.get_serializer(qs, many=True)
            return Response(serializer.data)
        except Exception:
            return Response(
                {'detail': 'No se encontraron citas para este paciente'},
                status=status.HTTP_404_NOT_FOUND
            )


# =============================================================================
# HORARIOS DE ATENCIÓN
# =============================================================================

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
        """
        - Administrador/Asistente: todos los horarios.
        - Odontólogo: solo sus propios horarios de atención.
        """
        activo_param = self.request.query_params.get("activo")
        qs = HorarioAtencion.objects.select_related('odontologo').order_by(
            'dia_semana', 'hora_inicio'
        )

        if activo_param is not None:
            activo = activo_param.lower() == 'true'
            qs = qs.filter(activo=activo)

        # Filtro por rol
        if not _usuario_ve_todas_las_citas(self.request.user):
            qs = qs.filter(odontologo=self.request.user)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        logger.info(f"Horario de atención creado por {request.user.username}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
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
            return Response(
                {'detail': 'Error interno del servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.activo = False
        instance.save()
        logger.info(f"Horario {instance.id} desactivado por {request.user.username}")
        return Response({'id': str(instance.id)}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['get'],
        url_path='por-odontologo/(?P<odontologo_id>[^/.]+)'
    )
    def por_odontologo(self, request, odontologo_id=None):
        """
        Obtener horarios de un odontólogo.
        Odontólogo solo puede consultar sus propios horarios.
        """
        efectivo_id = (
            odontologo_id
            if _usuario_ve_todas_las_citas(request.user)
            else str(request.user.id)
        )
        horarios = HorarioAtencionService.obtener_horarios_por_odontologo(efectivo_id)
        serializer = self.get_serializer(horarios, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='horarios-disponibles')
    def horarios_disponibles(self, request):
        serializer = HorariosDisponiblesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        horarios = CitaService.obtener_horarios_disponibles(
            serializer.validated_data['odontologo'],
            serializer.validated_data['fecha'],
            serializer.validated_data.get('duracion', 30)
        )
        return Response({'horarios_disponibles': horarios})


# =============================================================================
# RECORDATORIOS
# =============================================================================

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