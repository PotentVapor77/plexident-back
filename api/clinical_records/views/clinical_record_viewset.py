# src/api/clinical_records/views/clinical_record_viewset.py
"""
ViewSet principal para gestión de historiales clínicos
"""
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.exceptions import ValidationError

from api.clinical_records.models import ClinicalRecord
from api.clinical_records.serializers import (
    ClinicalRecordSerializer,
    ClinicalRecordDetailSerializer,
    ClinicalRecordCreateSerializer,
    ClinicalRecordCloseSerializer,
    ClinicalRecordReopenSerializer,
)
from api.clinical_records.services.clinical_record_service import ClinicalRecordService
from api.patients.models.paciente import Paciente
from api.clinical_records.serializers.form033_snapshot_serializer import Form033SnapshotSerializer
from api.clinical_records.services.form033_storage_service import Form033StorageService
from api.clinical_records.repositories.clinical_record_repository import ClinicalRecordRepository
from api.clinical_records.serializers.medical_history import WritableAntecedentesFamiliaresSerializer, WritableAntecedentesPersonalesSerializer
from api.clinical_records.serializers.stomatognathic_exam import WritableExamenEstomatognaticoSerializer
from api.clinical_records.serializers.vital_signs import WritableConstantesVitalesSerializer
from api.clinical_records.services.vital_signs_service import VitalSignsService
from api.clinical_records.serializers.oral_health_indicators import OralHealthIndicatorsSerializer
from api.odontogram.models import IndiceCariesSnapshot
from api.odontogram.serializers.indices_caries_serializers import WritableIndiceCariesSnapshotSerializer
from api.clinical_records.serializers.indices_caries_serializers import WritableIndicesCariesSerializer

from .base import (
    ClinicalRecordPagination,
    BasePermissionMixin,
    QuerysetOptimizationMixin,
    SearchFilterMixin,
    ActiveFilterMixin,
    LoggingMixin,
    logger,
)


class ClinicalRecordViewSet(
    BasePermissionMixin,
    QuerysetOptimizationMixin,
    SearchFilterMixin,
    ActiveFilterMixin,
    LoggingMixin,
    viewsets.ModelViewSet,
):
    """
    ViewSet para gestión completa de historiales clínicos
    
    Endpoints:
        - GET    /api/clinical-records/                  - Listar historiales
        - GET    /api/clinical-records/{id}/             - Detalle de historial
        - GET    /api/clinical-records/by-paciente/      - Historiales por paciente
        - GET    /api/clinical-records/cargar-datos-iniciales/ - Pre-cargar datos
        - POST   /api/clinical-records/                  - Crear historial
        - POST   /api/clinical-records/{id}/cerrar/      - Cerrar historial
        - POST   /api/clinical-records/{id}/reabrir/     - Reabrir historial
        - PATCH  /api/clinical-records/{id}/             - Actualizar historial
        - DELETE /api/clinical-records/{id}/             - Eliminar (lógico)
    """
    
    queryset = ClinicalRecord.objects.all()
    permission_model_name = 'historia_clinica'
    pagination_class = ClinicalRecordPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['paciente', 'odontologo_responsable', 'estado', 'activo']
    ordering_fields = ['fecha_atencion', 'fecha_creacion', 'fecha_cierre']
    ordering = ['-fecha_atencion']
    
    # Campos para optimización de queryset
    RELATED_FIELDS = [
        'paciente',
        'odontologo_responsable',
        'antecedentes_personales',
        'antecedentes_familiares',
        'constantes_vitales',
        'examen_estomatognatico',
        'indicadores_salud_bucal', 
        'creado_por',
    ]
    
    # Campos para búsqueda
    SEARCH_FIELDS = [
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__cedula_pasaporte',
        'motivo_consulta',
        'odontologo_responsable__nombres',
        'odontologo_responsable__apellidos',
    ]
    
    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción"""
        if self.action == 'create':
            return ClinicalRecordCreateSerializer
        elif self.action in ['update', 'partial_update', 'retrieve']:
            return ClinicalRecordDetailSerializer
        return ClinicalRecordSerializer
    
    def get_queryset(self):
        """Queryset optimizado con filtros y búsqueda"""
        qs = self.queryset.order_by('-fecha_atencion')
        
        # Optimización con select_related
        qs = self.get_optimized_queryset(qs, self.RELATED_FIELDS)
        
        # Filtro de activo/inactivo
        qs = self.apply_active_filter(qs, self.request)
        
        # Búsqueda
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = self.apply_search_filter(qs, search, self.SEARCH_FIELDS)
        
        return qs
    
    def create(self, request, *args, **kwargs):
        """Crear nuevo historial clínico con datos pre-cargados"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            historial = ClinicalRecordService.crear_historial(
                serializer.validated_data
            )
            output_serializer = ClinicalRecordDetailSerializer(historial)
            
            self.log_create(historial, request.user)
            
            return Response(
                output_serializer.data,
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            self.log_error('crear historial', e, request.user)
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """Actualización completa o parcial de historial"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        
        self.perform_update(serializer)
        self.log_update(instance, request.user)
        
        return Response(serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminación lógica del historial"""
        instance = self.get_object()
        
        ClinicalRecordService.eliminar_historial(instance.id)
        self.log_delete(instance, request.user)
        
        return Response(
            {'id': str(instance.id)},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], url_path='cerrar')
    def cerrar(self, request, pk=None):
        """
        Cerrar un historial clínico (no permite más ediciones)
        
        POST: /api/clinical-records/{id}/cerrar/
        Body: {"observaciones_cierre": "texto opcional"}
        """
        serializer = ClinicalRecordCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            historial = ClinicalRecordService.cerrar_historial(pk, request.user)
            
            # Guardar observaciones de cierre si se proporcionan
            observaciones = serializer.validated_data.get('observaciones_cierre')
            if observaciones:
                historial.observaciones += (
                    f"\n\nObservaciones de cierre: {observaciones}"
                )
                historial.save()
            
            output_serializer = ClinicalRecordDetailSerializer(historial)
            
            logger.info(
                f"Historial clínico {pk} cerrado por {request.user.username}"
            )
            
            return Response(output_serializer.data)
        except ValidationError as e:
            logger.warning(
                f"Error cerrando historial {pk}: {str(e)} - "
                f"Usuario: {request.user.username}"
            )
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], url_path='reabrir')
    def reabrir(self, request, pk=None):
        """
        Reabrir un historial cerrado (acción sensible)
        
        POST: /api/clinical-records/{id}/reabrir/
        Body: {"motivo_reapertura": "texto requerido"}
        """
        serializer = ClinicalRecordReopenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            historial = ClinicalRecordService.reabrir_historial(pk, request.user)
            
            # Registrar motivo de reapertura
            motivo = serializer.validated_data['motivo_reapertura']
            historial.observaciones += (
                f"\n\nREABIERTO: {motivo} "
                f"(por {request.user.get_full_name()})"
            )
            historial.save()
            
            output_serializer = ClinicalRecordDetailSerializer(historial)
            
            logger.warning(
                f"Historial clínico {pk} reabierto por {request.user.username}. "
                f"Motivo: {motivo}"
            )
            
            return Response(output_serializer.data)
        except ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], url_path='by-paciente')
    def by_paciente(self, request):
        """
        Obtener todos los historiales de un paciente con información detallada
        
        GET: /api/clinical-records/by-paciente/?paciente_id={uuid}
        """
        paciente_id = request.query_params.get('paciente_id')
        
        if not paciente_id:
            return Response(
                {'detail': 'El parámetro paciente_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Queryset optimizado
            historiales = ClinicalRecord.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).select_related(
                *self.RELATED_FIELDS,
                'actualizado_por'
            ).order_by('-fecha_atencion')
            
            serializer = ClinicalRecordDetailSerializer(historiales, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(
                f"Error obteniendo historiales del paciente {paciente_id}: "
                f"{str(e)}"
            )
            return Response(
                {'detail': 'No se encontraron historiales para este paciente'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'], url_path='cargar-datos-iniciales')
    def cargar_datos_iniciales(self, request):
        """
        Retorna los datos iniciales para el formulario
        (últimos antecedentes, datos del paciente, etc.)
        
        GET: /api/clinical-records/cargar-datos-iniciales/?paciente_id={uuid}
        """
        paciente_id = request.query_params.get('paciente_id')
        
        if not paciente_id:
            return Response(
                {'detail': 'El parámetro paciente_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = ClinicalRecordService.cargar_datos_iniciales_paciente(
                paciente_id
            )
            return Response(data, status=status.HTTP_200_OK)
        except Paciente.DoesNotExist:
            return Response(
                {'detail': 'Paciente no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error cargando datos iniciales: {str(e)}")
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @action(detail=True, methods=['post'], url_path='agregar-form033')
    def agregar_form033(self, request, pk=None):
        """
        Agregar o actualizar snapshot del Form033 a un historial existente
        
        POST: /api/clinical-records/{id}/agregar-form033/
        Body: 
        {
            "form033_data": { ... estructura del odontograma ... },
            "observaciones": "texto opcional"
        }
        """
        historial = self.get_object()
        
        # Validar que el historial no esté cerrado
        if historial.estado == 'CERRADO':
            return Response(
                {'detail': 'No se puede modificar un historial cerrado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        form033_data = request.data.get('form033_data')
        if not form033_data:
            return Response(
                {'detail': 'Se requiere form033_data'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        observaciones = request.data.get('observaciones', '')
        
        try:
            snapshot = ClinicalRecordService.agregar_form033_a_historial(
                historial_id=pk,
                form033_data=form033_data,
                usuario=request.user,
                observaciones=observaciones
            )
            
            serializer = Form033SnapshotSerializer(snapshot)
            
            logger.info(
                f"Form033 agregado/actualizado en historial {pk} "
                f"por {request.user.username}"
            )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            logger.warning(
                f"Error agregando Form033 a historial {pk}: {str(e)}"
            )
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    
    @action(detail=True, methods=['get'], url_path='obtener-form033')
    def obtener_form033(self, request, pk=None):
        """
        Obtener snapshot del Form033 asociado a un historial
        
        GET: /api/clinical-records/{id}/obtener-form033/
        """
        try:
            snapshot = Form033StorageService.obtener_snapshot_por_historial(pk)
            
            if not snapshot:
                return Response(
                    {'detail': 'Este historial no tiene odontograma asociado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = Form033SnapshotSerializer(snapshot)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                f"Error obteniendo Form033 de historial {pk}: {str(e)}"
            )
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
    @action(detail=True, methods=['delete'], url_path='eliminar-form033')
    def eliminar_form033(self, request, pk=None):
        """
        Eliminar (lógicamente) el snapshot del Form033 de un historial
        
        DELETE: /api/clinical-records/{id}/eliminar-form033/
        """
        historial = self.get_object()
        
        # Validar que el historial no esté cerrado
        if historial.estado == 'CERRADO':
            return Response(
                {'detail': 'No se puede modificar un historial cerrado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            snapshot = Form033StorageService.obtener_snapshot_por_historial(pk)
            
            if not snapshot:
                return Response(
                    {'detail': 'Este historial no tiene odontograma asociado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            Form033StorageService.eliminar_snapshot(snapshot.id)
            
            logger.info(
                f"Form033 eliminado de historial {pk} por {request.user.username}"
            )
            
            return Response(
                {'detail': 'Odontograma eliminado exitosamente'},
                status=status.HTTP_200_OK
            )
            
        except ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
            
            
    def _validar_puede_recargar(self, paciente_id):
        """
        Busca el historial más reciente y valida que sea BORRADOR.
        """
        # Usamos filter().first() para evitar errores si no existe
        ultimo_historial = ClinicalRecord.objects.filter(
            paciente__id=paciente_id, # Usamos la relación paciente__id
            activo=True
        ).order_by('-fecha_creacion').first()
        
        if not ultimo_historial:
            return None, "No se encontró un historial clínico activo para este paciente."
        
        if ultimo_historial.estado != 'BORRADOR':
            return None, f"El historial debe estar en BORRADOR (Actual: {ultimo_historial.estado})"
            
        return ultimo_historial, None
    
    @action(detail=True, methods=['get'], url_path='indicadores-salud-bucal')
    def obtener_indicadores_historial(self, request, pk=None):
        """
        Obtiene los indicadores de salud bucal asociados a este historial específico (FK).
        GET: /api/clinical-records/{id}/indicadores-salud-bucal/
        """
        historial = self.get_object()
        
        if historial.indicadores_salud_bucal:
            
            serializer = OralHealthIndicatorsSerializer(historial.indicadores_salud_bucal)
            return Response({
                'success': True,
                'message': 'Indicadores del historial',
                'data': serializer.data,
                'source': 'historial_fk'  
            })
        
        from api.clinical_records.services.indicadores_service import ClinicalRecordIndicadoresService
        
        indicadores = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(
            str(historial.paciente_id)
        )
        
        if indicadores:
            
            serializer = OralHealthIndicatorsSerializer(indicadores)
            
            return Response({
                'success': True,
                'message': 'Indicadores más recientes del paciente (no asociados a este historial)',
                'data': serializer.data,
                'source': 'paciente_latest',  
                'warning': 'Este historial no tiene indicadores asociados específicamente'
            })
        
        return Response({
            'success': False,
            'message': 'No hay indicadores de salud bucal para este historial ni para el paciente',
            'data': None
        }, status=status.HTTP_404_NOT_FOUND)


    @action(detail=True, methods=['post'], url_path='guardar-indicadores-salud-bucal')
    def guardar_indicadores_salud_bucal(self, request, pk=None):
        """
        Guarda nuevos indicadores de salud bucal y los asocia a este historial (FK).
        
        POST: /api/clinical-records/{id}/guardar-indicadores-salud-bucal/
        Body: { ...datos de indicadores... }
        """
        historial = self.get_object()
        
        # Validar que el historial no esté cerrado
        if historial.estado == 'CERRADO':
            return Response({
                'success': False,
                'message': 'No se pueden agregar indicadores a un historial cerrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from odontogram.models import IndicadoresSaludBucal
            
            # Validar datos
            serializer = OralHealthIndicatorsSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Crear nuevos indicadores
            indicadores = IndicadoresSaludBucal.objects.create(
                paciente=historial.paciente,
                creado_por=request.user,
                **serializer.validated_data
            )
            
            historial.indicadores_salud_bucal = indicadores
            historial.save(update_fields=['indicadores_salud_bucal'])
            
            
            output_serializer = OralHealthIndicatorsSerializer(indicadores)
            
            logger.info(
                f"Indicadores {indicadores.id} guardados y asociados "
                f"al historial {pk} por {request.user.username}"
            )
            
            return Response({
                'success': True,
                'message': 'Indicadores guardados y asociados al historial exitosamente',
                'data': output_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            logger.error(f"Error validando indicadores para historial {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error de validación',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error guardando indicadores para historial {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error guardando indicadores: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=True, methods=['patch'], url_path='actualizar-indicadores-salud-bucal')
    def actualizar_indicadores_salud_bucal(self, request, pk=None):
        """
        Actualiza los indicadores de salud bucal asociados a este historial.
        PATCH: /api/clinical-records/{id}/actualizar-indicadores-salud-bucal/
        """
        historial = self.get_object()
        
        # Validar que el historial no esté cerrado
        if historial.estado == 'CERRADO':
            return Response(
                {'detail': 'No se puede modificar un historial cerrado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que el historial tenga indicadores asociados
        if not historial.indicadores_salud_bucal:
            return Response(
                {
                    'detail': 'Este historial no tiene indicadores asociados. '
                            'Use el endpoint guardar-indicadores-salud-bucal para crear nuevos.'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Actualizar los indicadores existentes
        serializer = OralHealthIndicatorsSerializer(
            historial.indicadores_salud_bucal,
            data=request.data,
            partial=True
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            indicadores = serializer.save()
            
            
            return Response({
                'success': True,
                'message': 'Indicadores actualizados exitosamente',
                'data': OralHealthIndicatorsSerializer(indicadores).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                f"Error actualizando indicadores para historial {pk}: {str(e)}"
            )
            return Response(
                {'detail': f'Error al actualizar indicadores: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
            
    @action(detail=True, methods=['post'], url_path='guardar-indices-caries')
    def guardar_indices_caries(self, request, pk=None):
        """
        Guarda nuevos índices de caries y los asocia al historial
        POST: /api/clinical-records/{id}/guardar-indices-caries/
        
        Body puede contener:
        1. indices_caries_id: ID de registro existente
        2. Datos completos para crear nuevo registro
        """
        historial = self.get_object()
        
        # Validar que el historial no esté cerrado
        if historial.estado == 'CERRADO':
            return Response({
                'detail': 'No se pueden agregar índices a un historial cerrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            indices_caries_id = request.data.get('indices_caries_id')
            if indices_caries_id:
                try:
                    indices = IndiceCariesSnapshot.objects.get(
                        id=indices_caries_id,
                        paciente=historial.paciente,
                        activo=True
                    )
                    historial.indices_caries = indices
                    historial.save(update_fields=['indices_caries'])
                    
                    logger.info(f"Índices {indices.id} asociados al historial {pk}")
                    
                    return Response({
                        'success': True,
                        'message': 'Índices asociados exitosamente',
                        'data': WritableIndicesCariesSerializer(indices).data
                    }, status=status.HTTP_200_OK)
                    
                except IndiceCariesSnapshot.DoesNotExist:
                    return Response({
                        'detail': 'Los índices especificados no existen o no pertenecen al paciente'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = WritableIndicesCariesSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Crear nuevos índices
            indices = IndiceCariesSnapshot.objects.create(
                paciente=historial.paciente,
                creado_por=request.user,
                **serializer.validated_data
            )
            
            # Asociar al historial
            historial.indices_caries = indices
            historial.save(update_fields=['indices_caries'])
            
            logger.info(f"Índices {indices.id} creados y asociados al historial {pk}")
            
            return Response({
                'success': True,
                'message': 'Índices creados y asociados exitosamente',
                'data': WritableIndicesCariesSerializer(indices).data
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({
                'success': False,
                'message': 'Error de validación',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error guardando índices para historial {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error guardando índices: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['patch'], url_path='actualizar-indices-caries')
    def actualizar_indices_caries(self, request, pk=None):
        """
        Actualiza los índices de caries asociados al historial
        PATCH: /api/clinical-records/{id}/actualizar-indices-caries/
        """
        historial = self.get_object()
        
        # Validar que el historial no esté cerrado
        if historial.estado == 'CERRADO':
            return Response({
                'detail': 'No se puede modificar un historial cerrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar que el historial tenga índices asociados
        if not historial.indices_caries:
            return Response({
                'detail': 'Este historial no tiene índices de caries asociados. '
                          'Use el endpoint guardar-indices-caries para crear nuevos.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Actualizar los índices existentes
        
        
        serializer = WritableIndicesCariesSerializer(
            historial.indices_caries,
            data=request.data,
            partial=True
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            indices = serializer.save()
            
            logger.info(f"Índices {indices.id} actualizados para historial {pk}")
            
            return Response({
                'success': True,
                'message': 'Índices actualizados exitosamente',
                'data': WritableIndicesCariesSerializer(indices).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error actualizando índices para historial {pk}: {str(e)}")
            return Response({
                'detail': f'Error al actualizar índices: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path=r'antecedentes-personales/(?P<paciente_id>[^/]+)/latest')
    def latest_antecedentes_personales(self, request, paciente_id=None):
        historial, error = self._validar_puede_recargar(paciente_id)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        datos = ClinicalRecordRepository.obtener_ultimos_datos_paciente(paciente_id)
        instancia = datos.get('antecedentes_personales')
        if not instancia:
            return Response({'detail': 'No hay datos previos'}, status=404)
        
        return Response(WritableAntecedentesPersonalesSerializer(instancia).data)

    @action(detail=False, methods=['get'], url_path=r'antecedentes-familiares/(?P<paciente_id>[^/]+)/latest')
    def latest_antecedentes_familiares(self, request, paciente_id=None):
        historial, error = self._validar_puede_recargar(paciente_id)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        datos = ClinicalRecordRepository.obtener_ultimos_datos_paciente(paciente_id)
        instancia = datos.get('antecedentes_familiares')
        if not instancia:
            return Response({'detail': 'No hay datos previos'}, status=404)
        
        return Response(WritableAntecedentesFamiliaresSerializer(instancia).data)

    @action(detail=False, methods=['get'], url_path=r'constantes-vitales/(?P<paciente_id>[^/]+)/latest')
    def latest_constantes_vitales(self, request, paciente_id=None):
        historial, error = self._validar_puede_recargar(paciente_id)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        instancia = VitalSignsService.obtener_ultima_constante(paciente_id)
        if not instancia:
            return Response({'detail': 'No hay datos previos'}, status=404)
        
        return Response(WritableConstantesVitalesSerializer(instancia).data)

    @action(detail=False, methods=['get'], url_path=r'examen-estomatognatico/(?P<paciente_id>[^/]+)/latest')
    def latest_examen_estomatognatico(self, request, paciente_id=None):
        historial, error = self._validar_puede_recargar(paciente_id)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        datos = ClinicalRecordRepository.obtener_ultimos_datos_paciente(paciente_id)
        instancia = datos.get('examen_estomatognatico')
        if not instancia:
            return Response({'detail': 'No hay datos previos'}, status=404)
        
        return Response(WritableExamenEstomatognaticoSerializer(instancia).data)

    @action(detail=False, methods=['get'], url_path=r'odontograma-2d/(?P<paciente_id>[^/]+)/latest')
    def latest_odontograma(self, request, paciente_id=None):
        historial, error = self._validar_puede_recargar(paciente_id)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        # Usar el historial actual para buscar el snapshot previo
        snapshot = Form033StorageService.obtener_snapshot_por_historial(historial.id)
        if not snapshot:
            return Response({'detail': 'No hay odontograma previo'}, status=404)
            
        return Response(Form033SnapshotSerializer(snapshot).data)
    
    # lastes de Indicadores de Salud Bucal
    @action(detail=False, methods=['get'], url_path=r'indicadores-salud-bucal/(?P<paciente_id>[^/]+)/latest')
    def latest_indicadores_salud(self, request, paciente_id=None):
        """
        Obtiene los indicadores de salud bucal más recientes (Read-only).
        """
        
        from api.clinical_records.services.indicadores_service import ClinicalRecordIndicadoresService
        from api.clinical_records.serializers.oral_health_indicators import OralHealthIndicatorsSerializer

        indicadores = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(paciente_id)
        
        if not indicadores:
            return Response(
                {'detail': 'No hay registros de indicadores para este paciente.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = OralHealthIndicatorsSerializer(indicadores)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path=r'indices-caries/(?P<paciente_id>[^/]+)/latest')
    def latest_indices_caries(self, request, paciente_id=None):
        """
        GET: /api/clinical-records/indices-caries/{paciente_id}/latest/
        """
        logger.info(f" Solicitando índices para paciente: {paciente_id}")
        
        historial, error = self._validar_puede_recargar(paciente_id)
        if error:
            logger.warning(f" Validación falló: {error}") 
            pass  
        
        logger.info(f" Buscando índices en base de datos...")
        
        datos = ClinicalRecordRepository.obtener_ultimos_datos_paciente(paciente_id)
        instancia = datos.get('indices_caries')
        
        logger.info(f" Índices encontrados: {instancia}")
        
        if not instancia:
            logger.warning(f" No se encontraron índices para paciente {paciente_id}")
            return Response({
                'detail': 'No hay índices de caries previos registrados',
                'disponible': False
            }, status=status.HTTP_404_NOT_FOUND)
        
        
        serializer_data = WritableIndicesCariesSerializer(instancia).data
        
        logger.info(f"Retornando datos: {serializer_data}")
        
        return Response(serializer_data)