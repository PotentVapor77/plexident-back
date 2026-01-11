import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Q, Prefetch
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.odontogram.models import PlanTratamiento, SesionTratamiento
from api.odontogram.serializers.plan_tratamiento_serializers import (
    PlanTratamientoListSerializer,
    PlanTratamientoDetailSerializer,
    PlanTratamientoCreateSerializer,
    SesionTratamientoListSerializer,
    SesionTratamientoDetailSerializer,
    SesionTratamientoCreateSerializer
)
from api.odontogram.services.plan_tratamiento_service import PlanTratamientoService

logger = logging.getLogger(__name__)


class PlanTratamientoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Planes de Tratamiento Dental
    
    list: Listar planes de tratamiento activos
    create: Crear un nuevo plan
    retrieve: Obtener detalle de un plan específico
    update: Actualizar un plan completo
    partial_update: Actualizar campos específicos de un plan
    destroy: Eliminación lógica de un plan
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Queryset optimizado con filtros y anotaciones
        """
        user = self.request.user
        queryset = PlanTratamiento.objects.filter(activo=True)
        
        # Filtro por paciente
        paciente_id = self.request.query_params.get('paciente_id')
        if paciente_id:
            queryset = queryset.filter(paciente_id=paciente_id)
        
        # Filtro por odontólogo creador (útil para "mis planes")
        creado_por_mi = self.request.query_params.get('creado_por_mi')
        if creado_por_mi and creado_por_mi.lower() == 'true':
            queryset = queryset.filter(creado_por=user)
        
        # Filtro por fecha de creación
        fecha_desde = self.request.query_params.get('fecha_desde')
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        
        if fecha_desde:
            queryset = queryset.filter(fecha_creacion__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_creacion__lte=fecha_hasta)
        
        # Optimizaciones según la acción
        if self.action == 'list':
            # Para listado: solo count de sesiones
            queryset = queryset.select_related(
                'paciente', 
                'creado_por'
            ).annotate(
                total_sesiones=Count('sesiones', filter=Q(sesiones__activo=True)),
                sesiones_completadas=Count(
                    'sesiones', 
                    filter=Q(sesiones__activo=True, sesiones__estado='completada')
                )
            )
        else:
            # Para detalle: prefetch completo
            queryset = queryset.select_related(
                'paciente', 
                'creado_por'
            ).prefetch_related(
                Prefetch(
                    'sesiones',
                    queryset=SesionTratamiento.objects.filter(activo=True).order_by('numero_sesion')
                )
            )
        
        return queryset.order_by('-fecha_creacion')
    
    def get_serializer_class(self):
        """Serializer dinámico según acción"""
        if self.action == 'retrieve':
            return PlanTratamientoDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PlanTratamientoCreateSerializer
        return PlanTratamientoListSerializer
    
    def perform_create(self, serializer):
        """
        Creación de plan con manejo robusto de errores
        """
        try:
            service = PlanTratamientoService()
            paciente_id = serializer.validated_data['paciente'].id
            
            plan = service.crear_plan_tratamiento(
                paciente_id=str(paciente_id),
                odontologo_id=self.request.user.id,
                titulo=serializer.validated_data.get('titulo', 'Plan de Tratamiento'),
                notas_generales=serializer.validated_data.get('notas_generales', ''),
                usar_ultimo_odontograma=serializer.validated_data.get('usar_ultimo_odontograma', True)
            )
            
            # ✅ CORRECCIÓN YA APLICADA
            serializer.instance = plan
            
            logger.info(
                f"Plan creado exitosamente",
                extra={
                    'plan_id': str(plan.id),
                    'user_id': self.request.user.id,
                    'paciente_id': str(paciente_id)
                }
            )
            
            return plan
            
        except ValidationError as e:
            logger.warning(f"Validación fallida al crear plan: {str(e)}")
            raise DRFValidationError(detail=str(e))
        except Exception as e:
            logger.error(
                f"Error inesperado al crear plan",
                exc_info=True,
                extra={'user_id': self.request.user.id}
            )
            raise DRFValidationError(detail="Error interno al crear el plan")
    
    def perform_update(self, serializer):
        """
        Actualización de plan con validaciones
        """
        try:
            instance = serializer.save()
            
            logger.info(
                f"Plan actualizado",
                extra={
                    'plan_id': str(instance.id),
                    'user_id': self.request.user.id
                }
            )
            
        except ValidationError as e:
            raise DRFValidationError(detail=str(e))
    
    def destroy(self, request, *args, **kwargs):
        """
        Eliminación lógica con validaciones de negocio
        """
        plan = self.get_object()
        
        # Validar que no tenga sesiones en progreso
        sesiones_activas = plan.sesiones.filter(
            activo=True,
            estado__in=['planificada', 'en_progreso']
        ).count()
        
        if sesiones_activas > 0:
            logger.warning(
                f"Intento de eliminar plan con sesiones activas",
                extra={'plan_id': str(plan.id), 'sesiones_activas': sesiones_activas}
            )
            raise DRFValidationError(
                detail=f"No se puede eliminar el plan. Tiene {sesiones_activas} sesión(es) activa(s)"
            )
        
        try:
            plan.eliminar_logicamente(request.user)
            
            logger.info(
                f"Plan eliminado lógicamente",
                extra={
                    'plan_id': str(plan.id),
                    'user_id': request.user.id
                }
            )
            
            return Response(
                {'detail': 'Plan eliminado correctamente'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Exception as e:
            logger.error(f"Error al eliminar plan: {str(e)}", exc_info=True)
            raise DRFValidationError(detail="Error al eliminar el plan")
    
    @swagger_auto_schema(
        method='get',
        operation_description="Obtiene diagnósticos del último odontograma del paciente",
        responses={
            200: openapi.Response(
                description="Diagnósticos disponibles",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'version_odontograma': openapi.Schema(type=openapi.TYPE_STRING),
                        'fecha_odontograma': openapi.Schema(type=openapi.TYPE_STRING),
                        'total_diagnosticos': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'diagnosticos': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))
                    }
                )
            )
        }
    )
    @action(detail=True, methods=['get'])
    def diagnosticos_disponibles(self, request, pk=None):
        """
        GET /api/planes-tratamiento/{id}/diagnosticos-disponibles/
        Retorna diagnósticos del último odontograma para autocompletar
        """
        try:
            plan = self.get_object()
            service = PlanTratamientoService()
            
            diagnosticos_data = service.obtener_diagnosticos_ultimo_odontograma(
                str(plan.paciente.id)
            )
            
            return Response(diagnosticos_data, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error obteniendo diagnósticos: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Error obteniendo diagnósticos'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def estadisticas(self, request, pk=None):
        """
        GET /api/planes-tratamiento/{id}/estadisticas/
        Retorna estadísticas del plan de tratamiento
        """
        plan = self.get_object()
        
        sesiones = plan.sesiones.filter(activo=True)
        
        estadisticas = {
            'total_sesiones': sesiones.count(),
            'sesiones_por_estado': {
                'planificada': sesiones.filter(estado='planificada').count(),
                'en_progreso': sesiones.filter(estado='en_progreso').count(),
                'completada': sesiones.filter(estado='completada').count(),
                'cancelada': sesiones.filter(estado='cancelada').count(),
            },
            'progreso_porcentaje': 0,
            'fecha_ultima_sesion': None,
            'proxima_sesion': None
        }
        
        # Calcular progreso
        if estadisticas['total_sesiones'] > 0:
            completadas = estadisticas['sesiones_por_estado']['completada']
            estadisticas['progreso_porcentaje'] = round(
                (completadas / estadisticas['total_sesiones']) * 100, 2
            )
        
        # Última sesión
        ultima = sesiones.filter(fecha_realizacion__isnull=False).order_by('-fecha_realizacion').first()
        if ultima:
            estadisticas['fecha_ultima_sesion'] = ultima.fecha_realizacion.isoformat()
        
        # Próxima sesión
        proxima = sesiones.filter(
            estado='planificada',
            fecha_programada__gte=timezone.now()
        ).order_by('fecha_programada').first()
        
        if proxima:
            estadisticas['proxima_sesion'] = {
                'id': str(proxima.id),
                'fecha': proxima.fecha_programada.isoformat() if proxima.fecha_programada else None,
                'numero_sesion': proxima.numero_sesion
            }
        
        return Response(estadisticas, status=status.HTTP_200_OK)


class SesionTratamientoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Sesiones de Tratamiento
    
    Incluye actions especiales:
    - firmar: Firma digital de la sesión
    - completar: Marca como completada
    - cancelar: Cancela la sesión
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Queryset con filtros avanzados"""
        queryset = SesionTratamiento.objects.filter(activo=True)
        
        # Filtros por parámetros
        plan_id = self.request.query_params.get('plan_id')
        paciente_id = self.request.query_params.get('paciente_id')
        estado = self.request.query_params.get('estado')
        fecha_desde = self.request.query_params.get('fecha_desde')
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        
        if plan_id:
            queryset = queryset.filter(plan_tratamiento_id=plan_id)
        
        if paciente_id:
            queryset = queryset.filter(plan_tratamiento__paciente_id=paciente_id)
        
        if estado:
            queryset = queryset.filter(estado=estado)
        
        if fecha_desde:
            queryset = queryset.filter(fecha_programada__gte=fecha_desde)
        
        if fecha_hasta:
            queryset = queryset.filter(fecha_programada__lte=fecha_hasta)
        
        # Optimizaciones
        return queryset.select_related(
            'plan_tratamiento',
            'plan_tratamiento__paciente',
            'odontologo',
            'cita'
        ).order_by('plan_tratamiento', 'numero_sesion')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SesionTratamientoDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SesionTratamientoCreateSerializer
        return SesionTratamientoListSerializer
    
    def perform_create(self, serializer):
        """Creación de sesión con manejo robusto"""
        try:
            service = PlanTratamientoService()
            
            sesion = service.crear_sesion_tratamiento(
                plan_tratamiento_id=str(serializer.validated_data['plan_tratamiento'].id),
                odontologo_id=self.request.user.id,
                fecha_programada=serializer.validated_data.get('fecha_programada'),
                autocompletar_diagnosticos=serializer.validated_data.get('autocompletar_diagnosticos', True),
                procedimientos=serializer.validated_data.get('procedimientos', []),
                prescripciones=serializer.validated_data.get('prescripciones', []),
                notas=serializer.validated_data.get('notas', ''),
                cita_id=serializer.validated_data.get('cita_id'),
            )
            
            serializer.instance = sesion
            
            logger.info(
                f"Sesión creada exitosamente",
                extra={
                    'sesion_id': str(sesion.id),
                    'plan_id': str(sesion.plan_tratamiento_id),
                    'user_id': self.request.user.id
                }
            )
            
            return sesion
            
        except ValidationError as e:
            logger.warning(f"Validación fallida al crear sesión: {str(e)}")
            raise DRFValidationError(detail=str(e))
        except Exception as e:
            logger.error(f"Error al crear sesión", exc_info=True)
            raise DRFValidationError(detail="Error interno al crear la sesión")
    
    def destroy(self, request, *args, **kwargs):
        """Eliminación lógica con validaciones"""
        sesion = self.get_object()
        
        # No permitir eliminar sesiones completadas o firmadas
        if sesion.estado == SesionTratamiento.EstadoSesion.COMPLETADA:
            raise DRFValidationError(
                detail="No se puede eliminar una sesión completada"
            )
        
        # Si tiene firma, tampoco permitir (agregar lógica según tu modelo)
        # if sesion.firmada:
        #     raise DRFValidationError(detail="No se puede eliminar una sesión firmada")
        
        try:
            sesion.eliminar_logicamente(request.user)
            
            logger.info(
                f"Sesión eliminada",
                extra={'sesion_id': str(sesion.id), 'user_id': request.user.id}
            )
            
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Error al eliminar sesión: {str(e)}", exc_info=True)
            raise DRFValidationError(detail="Error al eliminar la sesión")
    
    @swagger_auto_schema(
        method='post',
        operation_description="Firma digitalmente una sesión de tratamiento",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'firma_digital': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Firma digital en base64 o hash'
                )
            }
        )
    )
    @action(detail=True, methods=['post'])
    def firmar(self, request, pk=None):
        """
        POST /api/sesiones-tratamiento/{id}/firmar/
        Body: { "firma_digital": "base64_string_or_hash" }
        """
        try:
            sesion = self.get_object()
            service = PlanTratamientoService()
            
            firma_digital = request.data.get('firma_digital')
            
            if not firma_digital:
                raise DRFValidationError(detail="La firma digital es requerida")
            
            sesion = service.firmar_sesion(
                sesion_id=str(sesion.id),
                odontologo_id=request.user.id,
                firma_digital=firma_digital
            )
            
            serializer = SesionTratamientoDetailSerializer(sesion)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error al firmar sesión: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Error al firmar la sesión'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def completar(self, request, pk=None):
        """
        POST /api/sesiones-tratamiento/{id}/completar/
        Marca la sesión como completada
        """
        try:
            sesion = self.get_object()
            
            # Validaciones
            if sesion.estado == SesionTratamiento.EstadoSesion.COMPLETADA:
                raise DRFValidationError(detail="La sesión ya está completada")
            
            if sesion.estado == SesionTratamiento.EstadoSesion.CANCELADA:
                raise DRFValidationError(detail="No se puede completar una sesión cancelada")
            
            # Actualizar estado
            sesion.estado = SesionTratamiento.EstadoSesion.COMPLETADA
            sesion.fecha_realizacion = timezone.now()
            sesion.save()
            
            logger.info(
                f"Sesión completada",
                extra={
                    'sesion_id': str(sesion.id),
                    'user_id': request.user.id
                }
            )
            
            serializer = SesionTratamientoDetailSerializer(sesion)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error al completar sesión: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Error al completar la sesión'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        POST /api/sesiones-tratamiento/{id}/cancelar/
        Body: { "motivo": "razón de cancelación" }
        """
        try:
            sesion = self.get_object()
            motivo = request.data.get('motivo', '')
            
            if sesion.estado == SesionTratamiento.EstadoSesion.COMPLETADA:
                raise DRFValidationError(detail="No se puede cancelar una sesión completada")
            
            sesion.estado = SesionTratamiento.EstadoSesion.CANCELADA
            
            # Agregar motivo a observaciones
            if motivo:
                observaciones_actuales = sesion.observaciones or ""
                sesion.observaciones = f"{observaciones_actuales}\n[CANCELACIÓN] {motivo}".strip()
            
            sesion.save()
            
            logger.info(
                f"Sesión cancelada",
                extra={
                    'sesion_id': str(sesion.id),
                    'user_id': request.user.id,
                    'motivo': motivo
                }
            )
            
            serializer = SesionTratamientoDetailSerializer(sesion)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
