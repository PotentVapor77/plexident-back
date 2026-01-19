from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from api.clinical_records.models import ClinicalRecord
from api.clinical_records.serializers import (
    ClinicalRecordSerializer,
    ClinicalRecordDetailSerializer,
    ClinicalRecordCreateSerializer,
    ClinicalRecordUpdateSerializer,
    ClinicalRecordCloseSerializer,
    ClinicalRecordReopenSerializer
)
from api.clinical_records.services import ClinicalRecordService
from api.users.permissions import UserBasedPermission
import logging

from api.patients.models.paciente import Paciente

logger = logging.getLogger(__name__)


class ClinicalRecordPagination(PageNumberPagination):
    """Configuración de paginación para historiales clínicos"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ClinicalRecordViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de historiales clínicos"""
    
    queryset = ClinicalRecord.objects.all()
    permission_classes = [IsAuthenticated, UserBasedPermission]
    permission_model_name = 'historia_clinica'
    pagination_class = ClinicalRecordPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['paciente', 'odontologo_responsable', 'estado', 'activo']
    ordering_fields = ['fecha_atencion', 'fecha_creacion', 'fecha_cierre']
    ordering = ['-fecha_atencion']

    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción"""
        if self.action == 'create':
            return ClinicalRecordCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ClinicalRecordDetailSerializer
        elif self.action == 'retrieve':
            return ClinicalRecordDetailSerializer
        return ClinicalRecordSerializer

    def get_queryset(self):
        """Queryset base con filtros y búsqueda"""
        request = self.request
        search = request.query_params.get('search', '').strip()
        activo_param = request.query_params.get('activo')
        
        qs = ClinicalRecord.objects.select_related(
            'paciente',
            'odontologo_responsable',
            'antecedentes_personales',
            'antecedentes_familiares',
            'constantes_vitales',
            'examen_estomatognatico',
            'creado_por'
        ).order_by('-fecha_atencion')
        
        if activo_param is not None:
            activo = activo_param.lower() == 'true'
            qs = qs.filter(activo=activo)
        else:
            qs = qs.filter(activo=True)
        
        if search:
            qs = qs.filter(
                Q(paciente__nombres__icontains=search) |
                Q(paciente__apellidos__icontains=search) |
                Q(paciente__cedula_pasaporte__icontains=search) |
                Q(motivo_consulta__icontains=search) |
                Q(odontologo_responsable__nombres__icontains=search) |
                Q(odontologo_responsable__apellidos__icontains=search)
            )
        
        return qs

    def create(self, request, *args, **kwargs):
        """Crear nuevo historial clínico con datos pre-cargados"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            historial = ClinicalRecordService.crear_historial(serializer.validated_data)
            output_serializer = ClinicalRecordDetailSerializer(historial)
            logger.info(f"Historial clínico creado para paciente {historial.paciente.nombre_completo} por {request.user.username}")
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            logger.error(f"Error creando historial clínico: {str(e)}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Actualizar historial clínico"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            historial = ClinicalRecordService.actualizar_historial(instance.id, serializer.validated_data)
            output_serializer = ClinicalRecordDetailSerializer(historial)
            logger.info(f"Historial clínico {historial.id} actualizado por {request.user.username}")
            return Response(output_serializer.data)
        except ValidationError as e:
            logger.error(f"Error actualizando historial clínico: {str(e)}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Eliminación lógica del historial"""
        instance = self.get_object()
        ClinicalRecordService.eliminar_historial(instance.id)
        logger.info(f"Historial clínico {instance.id} desactivado por {request.user.username}")
        return Response({'id': str(instance.id)}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='cerrar')
    def cerrar(self, request, pk=None):
        """
        Cerrar un historial clínico (no permite más ediciones).
        POST: /api/clinical-records/<id>/cerrar/
        """
        serializer = ClinicalRecordCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            historial = ClinicalRecordService.cerrar_historial(pk, request.user)
            
            # Guardar observaciones de cierre si se proporcionan
            if serializer.validated_data.get('observaciones_cierre'):
                historial.observaciones += f"\n\nObservaciones de cierre: {serializer.validated_data['observaciones_cierre']}"
                historial.save()
            
            output_serializer = ClinicalRecordDetailSerializer(historial)
            logger.info(f"Historial clínico {pk} cerrado por {request.user.username}")
            return Response(output_serializer.data)
        except ValidationError as e:
            logger.warning(f"Error cerrando historial {pk}: {str(e)} - Usuario: {request.user.username}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='reabrir')
    def reabrir(self, request, pk=None):
        """
        Reabrir un historial cerrado (acción sensible).
        POST: /api/clinical-records/<id>/reabrir/
        """
        serializer = ClinicalRecordReopenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            historial = ClinicalRecordService.reabrir_historial(pk, request.user)
            
            # Registrar motivo de reapertura
            historial.observaciones += f"\n\nREABIERTO: {serializer.validated_data['motivo_reapertura']} (por {request.user.get_full_name()})"
            historial.save()
            
            output_serializer = ClinicalRecordDetailSerializer(historial)
            logger.warning(f"Historial clínico {pk} reabierto por {request.user.username}. Motivo: {serializer.validated_data['motivo_reapertura']}")
            return Response(output_serializer.data)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='by-paciente')
    def by_paciente(self, request, paciente_id=None):
        """
        Obtener todos los historiales de un paciente con información detallada.
        GET: /api/clinical-records/by-paciente/?paciente_id=<uuid>
        """
        paciente_id = request.query_params.get('paciente_id')
        
        if not paciente_id:
            return Response(
                {'detail': 'El parámetro paciente_id es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Usar el mismo queryset optimizado con select_related
            historiales = ClinicalRecord.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).select_related(
                'paciente',
                'odontologo_responsable',
                'antecedentes_personales',
                'antecedentes_familiares',
                'constantes_vitales',
                'examen_estomatognatico',
                'creado_por',
                'actualizado_por'
            ).order_by('-fecha_atencion')
            
            # Usar el serializer detallado en lugar del básico
            serializer = ClinicalRecordDetailSerializer(historiales, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error obteniendo historiales del paciente {paciente_id}: {str(e)}")
            return Response(
                {'detail': 'No se encontraron historiales para este paciente'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='cargar-datos-iniciales')
    def cargar_datos_iniciales(self, request):
        """
        Retorna los datos iniciales para el formulario (últimos antecedentes, datos del paciente, etc.)
        GET: /api/clinical-records/cargar-datos-iniciales/?paciente_id=UUID
        """
        paciente_id = request.query_params.get('paciente_id')
        if not paciente_id:
            return Response(
                {'detail': 'El parámetro paciente_id es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            data = ClinicalRecordService.cargar_datos_iniciales_paciente(paciente_id)
            return Response(data, status=status.HTTP_200_OK)
        except Paciente.DoesNotExist:
             return Response({'detail': 'Paciente no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error cargando datos iniciales: {str(e)}")
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        




'''
EndPoints
GET	Listar todos los historiales
GET	/api/clinical-records/{id}/	Detalle de un historial
GET	/api/clinical-records/by-paciente/?paciente_id={uuid}	Historiales por paciente
GET	/api/clinical-records/cargar-datos-iniciales/?paciente_id={uuid}	Pre-cargar datos del paciente
POST	/api/clinical-records/	Crear nuevo historial
POST	/api/clinical-records/{id}/cerrar/	Cerrar historial
POST	/api/clinical-records/{id}/reabrir/	Reabrir historial
PATCH	/api/clinical-records/{id}/	Actualizar historial
DELETE	/api/clinical-records/{id}/	Eliminar (lógico) historial
Faltan aun los endPoints de lo demas bloques de form 033
'''