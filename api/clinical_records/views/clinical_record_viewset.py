# src/api/clinical_records/views/clinical_record_viewset.py
"""
ViewSet principal para gestión de historiales clínicos
"""
from django.conf import settings
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.exceptions import ValidationError

from api.clinical_records.serializers.clinical_record_with_plan_serializer import (
    ClinicalRecordWithPlanDetailSerializer,
    ClinicalRecordListSerializer,
    ClinicalRecordCreateSerializer as ClinicalRecordCreateSerializerNew
)


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
from api.odontogram.models import IndiceCariesSnapshot, PlanTratamiento, SesionTratamiento
from api.odontogram.serializers.indices_caries_serializers import WritableIndiceCariesSnapshotSerializer
from api.clinical_records.serializers.indices_caries_serializers import WritableIndicesCariesSerializer
from api.clinical_records.services.diagnostico_cie_service import DiagnosticosCIEService
from api.odontogram.views.diagnostico_cie_views import DiagnosticoCIEViewSet
from api.clinical_records.models.diagnostico_cie import DiagnosticoCIEHistorial
from api.clinical_records.serializers.plan_tratamiento_serializers import (
    PlanTratamientoCompletoSerializer,
    PlanTratamientoResumenSerializer
)
from api.clinical_records.serializers.examenes_complementarios import WritableExamenesComplementariosSerializer
from api.clinical_records.services.examenes_complementarios_service import ExamenesComplementariosLinkService




from .base import (
    ClinicalRecordPagination,
    BasePermissionMixin,
    DateRangeFilterMixin,
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
    DateRangeFilterMixin,
    LoggingMixin,
    viewsets.ModelViewSet,
):
    """
    ViewSet para gestión completa de historiales clínicos
    """
    
    queryset = ClinicalRecord.objects.all()
    permission_model_name = 'historia_clinica'
    pagination_class = ClinicalRecordPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['paciente', 'odontologo_responsable', 'estado', 'activo']
    ordering_fields = ['fecha_atencion', 'fecha_creacion', 'fecha_cierre']
    ordering = ['-fecha_atencion']
    
    # Campos para búsqueda (solo una definición)
    SEARCH_FIELDS = [
        # Paciente
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__nombre_completo',
        'paciente__cedula_pasaporte',
        
        # Campos del historial
        'motivo_consulta',
        'enfermedad_actual',
        'observaciones',
        'numero_historia_clinica_unica',
        'numero_archivo',
        
        # Odontólogo
        'odontologo_responsable__nombres',
        'odontologo_responsable__apellidos',
    ]
    
    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción"""
        if self.action == 'create':
            return ClinicalRecordCreateSerializerNew
        elif self.action == 'retrieve':
            return ClinicalRecordWithPlanDetailSerializer
        elif self.action == 'by_paciente':
            return ClinicalRecordDetailSerializer  
        elif self.action == 'list':
            return ClinicalRecordListSerializer
        elif self.action in ['update', 'partial_update']:
            return ClinicalRecordDetailSerializer
        return ClinicalRecordSerializer
    
    def get_queryset(self):
        """
        Queryset optimizado con filtro de activos/inactivos por defecto
        """
        qs = self.queryset.order_by('-fecha_atencion')
        
        # Optimización base con select_related
        qs = qs.select_related(
            'paciente',
            'odontologo_responsable',
            'antecedentes_personales',
            'antecedentes_familiares',
            'constantes_vitales',
            'examen_estomatognatico',
            'indicadores_salud_bucal',
            'indices_caries',  
            'creado_por',
            'plan_tratamiento',  
            'plan_tratamiento__paciente', 
            'plan_tratamiento__creado_por', 
            'examenes_complementarios',
        )
        
        if self.action in ['retrieve', 'by_paciente']:
            qs = qs.prefetch_related(
                'plan_tratamiento__sesiones', 
                'plan_tratamiento__sesiones__odontologo', 
            )
        
        # APLICAR FILTRO POR ACTIVO/INACTIVO
        # Por defecto, mostrar solo activos a menos que se solicite explícitamente inactivos
        qs = self.filter_by_active_status(qs, self.request)
        
        # Búsqueda
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = self.apply_search_filter(qs, search, self.SEARCH_FIELDS)
        
        return qs
    

    def filter_by_active_status(self, queryset, request):
        """
        Filtra el queryset según el parámetro 'activo' en los query params.
        
        Args:
            queryset: QuerySet a filtrar
            request: Request object con query_params
            
        Returns:
            QuerySet filtrado
            
        Parámetros de query:
            - activo=true: Solo registros activos (activo=True)
            - activo=false: Solo registros inactivos (activo=False)
            - sin parámetro: Todos los registros
        """
        activo_param = request.query_params.get('activo', None)
        
        if activo_param is not None:
            # Convertir a booleano
            activo_value = activo_param.lower() in ('true', '1', 'yes', 'si')
            queryset = queryset.filter(activo=activo_value)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Crear nuevo historial clínico con datos pre-cargados"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            historial = ClinicalRecordService.crear_historial(
                serializer.validated_data
            )
            output_serializer = ClinicalRecordDetailSerializer(historial)
            
            # Usar el método del mixin
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
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        if instance.estado == 'CERRADO':
            allowed_fields = {'observaciones', 'actualizado_por'}
            if not set(request.data.keys()).issubset(allowed_fields):
                return Response(
                    {'detail': 'No se puede modificar un historial cerrado'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        data = request.data.copy()

        # ── PLAN DE TRATAMIENTO (solo en BORRADOR) ─────────────────────
        # Sacar el valor antes de pasarlo al serializer, que lo ignora
        plan_id = data.pop('plan_tratamiento', None)
        # Por si el frontend envía el nombre alternativo plan_tratamiento_id
        if not plan_id:
            plan_id = data.pop('plan_tratamiento_id', None)
        # Si llegó como dict anidado {id: "..."}, extraer solo el id
        if isinstance(plan_id, dict):
            plan_id = plan_id.get('id')

        if plan_id:
            if instance.estado != 'BORRADOR':
                return Response(
                    {'detail': 'Solo se puede cambiar el plan de tratamiento cuando el historial está en BORRADOR'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                plan = PlanTratamiento.objects.get(
                    id=plan_id,
                    paciente=instance.paciente,
                    activo=True
                )
                instance.plan_tratamiento = plan
                instance.save(update_fields=['plan_tratamiento'])
                logger.info(
                    f"Plan {plan.id} vinculado al historial {instance.pk} "
                    f"por {request.user.username}"
                )
            except PlanTratamiento.DoesNotExist:
                return Response(
                    {'detail': 'Plan de tratamiento no encontrado o no pertenece al paciente'},
                    status=status.HTTP_404_NOT_FOUND
                )
        # ── FIN PLAN ───────────────────────────────────────────────────

        # ── SIGNOS VITALES ─────────────────────────────────────────────
        tiene_vitales_nuevos = VitalSignsService.tiene_datos_vitales(data)
        tiene_texto = VitalSignsService.tiene_datos_texto(data)

        if tiene_vitales_nuevos:
            nueva_constante = VitalSignsService.crear_constantes_vitales(
                paciente=instance.paciente,
                data=data,
                creado_por=request.user
            )
            instance.constantes_vitales = nueva_constante
            instance.constantes_vitales_nuevas = True
            instance.save(update_fields=['constantes_vitales', 'constantes_vitales_nuevas'])
            logger.info(
                f"Nuevas constantes vitales {nueva_constante.id} creadas "
                f"para historial {instance.pk}"
            )
        elif tiene_texto and instance.constantes_vitales:
            VitalSignsService.actualizar_constantes_existentes(
                instance.constantes_vitales, data
            )

        VitalSignsService.limpiar_campos_del_dict(data)
        # ── FIN VITALES ────────────────────────────────────────────────

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance.refresh_from_db()
        self.log_update(instance, request.user)

        output_serializer = self.get_serializer(instance)
        return Response(output_serializer.data)

    
    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminación lógica del historial"""
        instance = self.get_object()
        
        # Validar que no esté cerrado
        if instance.estado == 'CERRADO':
            return Response(
                {'detail': 'No se puede eliminar un historial cerrado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Eliminación lógica
        ClinicalRecordService.eliminar_historial(str(instance.id))
        
        # Refrescar para obtener el estado actualizado (activo=False)
        instance.refresh_from_db()
        
        # Usar el método del mixin
        self.log_delete(instance, request.user)
        
        return Response(
            {
                'success': True,
                'message': 'Historial eliminado correctamente',
                'id': str(instance.id)
            },
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
            # Obtener observaciones de cierre antes de cerrar
            observaciones_cierre = serializer.validated_data.get('observaciones_cierre')
            
            # Añadir observaciones al historial ANTES de cerrarlo
            if observaciones_cierre:
                historial = ClinicalRecordRepository.obtener_por_id(pk)
                historial.observaciones += f"\n\nObservaciones de cierre: {observaciones_cierre}"
                # Guardar solo el campo observaciones para evitar conflictos
                historial.save(update_fields=['observaciones'])
            
            # Ahora cerrar el historial
            historial = ClinicalRecordService.cerrar_historial(pk, request.user)
            
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
        except Exception as e:
            logger.error(
                f"Error inesperado cerrando historial {pk}: {str(e)}",
                exc_info=True
            )
            return Response(
                {'detail': 'Error al cerrar el historial clínico'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
        paciente_id = request.query_params.get('paciente_id') or request.query_params.get('pacienteid')

    
        if not paciente_id:
            return Response(
                {
                    "success": False,
                    "status_code": 400,
                    "message": "El parámetro paciente_id es requerido",
                    "data": None,
                    "errors": {"paciente_id": ["Este campo es requerido"]}
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validar que el paciente existe
            from api.patients.models.paciente import Paciente
            if not Paciente.objects.filter(id=paciente_id, activo=True).exists():
                return Response(
                    {
                        "success": False,
                        "status_code": 404,
                        "message": "Paciente no encontrado",
                        "data": None,
                        "errors": {"paciente_id": ["Paciente no encontrado o inactivo"]}
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Obtener queryset optimizado
            queryset = self.get_queryset().filter(paciente_id=paciente_id)
            
            # Aplicar filtro de activo si se especifica
            activo_param = request.query_params.get('activo')
            if activo_param is not None:
                activo_value = activo_param.lower() == 'true'
                queryset = queryset.filter(activo=activo_value)
            
            # Aplicar límite si se especifica
            limit = request.query_params.get('limit')
            if limit:
                try:
                    limit = int(limit)
                    queryset = queryset[:limit]
                except ValueError:
                    pass
            
            # Serializar con datos completos del plan
            serializer = self.get_serializer(queryset, many=True)
            
            return Response(
                {
                    "success": True,
                    "status_code": 200,
                    "message": "Historiales clínicos obtenidos exitosamente",
                    "count": queryset.count(),
                    "data": serializer.data,
                    "errors": None
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo historiales para paciente {paciente_id}: {str(e)}")
            return Response(
                {
                    "success": False,
                    "status_code": 500,
                    "message": "Error interno al obtener historiales",
                    "data": None,
                    "errors": {"detail": [str(e)]}
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='cargar-datos-iniciales')
    def cargar_datos_iniciales(self, request):
        """
        Retorna los datos iniciales para el formulario
        (últimos antecedentes, datos del paciente, etc.)
        
        GET: /api/clinical-records/cargar-datos-iniciales/?paciente_id={uuid}
        """
        paciente_id = request.query_params.get('paciente_id') or request.query_params.get('pacienteid')

    
        if not paciente_id:
            return Response(
                {"detail": "El parámetro pacienteid es requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            # Validar que el paciente existe
            paciente = Paciente.objects.get(id=paciente_id, activo=True)
        except Paciente.DoesNotExist:
            return Response(
                {"detail": "Paciente no encontrado o inactivo"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        try:
            # Cargar datos iniciales del paciente
            datos_iniciales = ClinicalRecordService.cargar_datos_iniciales_paciente(
                paciente_id
            )
            
            from api.clinical_records.services.plan_tratamiento_service import PlanTratamientoLinkService
            plan_activo = PlanTratamientoLinkService.obtener_plan_activo_paciente(
                paciente_id
            )
            
            if plan_activo:
                from api.clinical_records.serializers.plan_tratamiento_serializers import (
                    PlanTratamientoResumenSerializer
                )
                
                datos_iniciales['plan_tratamiento'] = {
                    'id': str(plan_activo.id),
                    'existe': True,
                    'resumen': PlanTratamientoResumenSerializer(plan_activo).data,
                    'mensaje': 'Se vinculará automáticamente al crear el historial'
                }
            else:
                datos_iniciales['plan_tratamiento'] = {
                    'id': None,
                    'existe': False,
                    'resumen': None,
                    'mensaje': 'No hay plan de tratamiento activo para este paciente'
                }
            
            # === EXÁMENES COMPLEMENTARIOS ===
            ultimo_examen = ExamenesComplementariosLinkService.obtener_ultimo_examen_paciente(
                paciente_id
            )
            
            if ultimo_examen:
                datos_iniciales['examenes_complementarios'] = {
                    'id': str(ultimo_examen.id),
                    'existe': True,
                    'data': WritableExamenesComplementariosSerializer(ultimo_examen).data,
                    'mensaje': 'Se vinculará automáticamente al crear el historial'
                }
            else:
                datos_iniciales['examenes_complementarios'] = {
                    'id': None,
                    'existe': False,
                    'data': None,
                    'mensaje': 'No hay exámenes complementarios previos para este paciente'
                }
            
            return Response(
                {
                    "success": True,
                    "status_code": 200,
                    "message": "Datos iniciales cargados correctamente",
                    "data": datos_iniciales,
                    "errors": None
                }
            )
            
        except Exception as e:
            logger.error(
                f"Error cargando datos iniciales para paciente {paciente_id}: {str(e)}"
            )
            return Response(
                {
                    "success": False,
                    "status_code": 500,
                    "message": "Error al cargar datos iniciales",
                    "data": None,
                    "errors": {"detail": [str(e)]}
                },
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
        
        FIX BRECHA 1: Ahora llama a PiezasIndiceService para registrar
        trazabilidad de piezas usadas (originales y suplentes).
        """
        historial = self.get_object()
        
        # Validar que el historial no esté cerrado
        if historial.estado == 'CERRADO':
            return Response({
                'success': False,
                'message': 'No se pueden agregar indicadores a un historial cerrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from api.odontogram.models import IndicadoresSaludBucal
            from api.odontogram.services.piezas_service import PiezasIndiceService
            from django.utils import timezone
            
            # Validar datos
            serializer = OralHealthIndicatorsSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # ===== FIX BRECHA 1: Obtener info de piezas y registrar trazabilidad =====
            paciente_id = str(historial.paciente_id)
            info_piezas = PiezasIndiceService.obtener_informacion_piezas(paciente_id)
            
            # Construir mapeo de piezas usadas con datos del registro
            piezas_mapeo = info_piezas.get('piezas_mapeo') or info_piezas.get('piezas', {})
            mapeo_piezas_usadas = {}
            
            for pieza_original, info in piezas_mapeo.items():
                pieza_usada = info.get('codigo_usado', pieza_original)
                
                # Verificar si hay datos para esta pieza en los validated_data
                tiene_datos = False
                datos_pieza = {}
                
                for campo in ['placa', 'calculo', 'gingivitis']:
                    campo_entrada = f"pieza_{pieza_original}_{campo}"
                    valor = serializer.validated_data.get(campo_entrada)
                    if valor is not None:
                        tiene_datos = True
                        datos_pieza[campo] = valor
                
                if tiene_datos:
                    mapeo_piezas_usadas[pieza_original] = {
                        'codigo_usado': pieza_usada,
                        'es_alternativa': info.get('es_alternativa', pieza_usada != pieza_original),
                        'codigo_original': pieza_original,
                        'disponible': info.get('disponible', True),
                        'diente_id': info.get('diente_id'),
                        'ambos_ausentes': info.get('ambos_ausentes', False),
                        'datos': datos_pieza
                    }
            
            piezas_usadas_en_registro = {
                'piezas_mapeo': mapeo_piezas_usadas,
                'denticion': info_piezas.get('denticion'),
                'estadisticas': info_piezas.get('estadisticas'),
                'fecha_registro': str(timezone.now())
            }
            # ===== FIN FIX BRECHA 1 =====
            
            # Crear nuevos indicadores CON trazabilidad de piezas
            indicadores = IndicadoresSaludBucal.objects.create(
                paciente=historial.paciente,
                creado_por=request.user,
                piezas_usadas_en_registro=piezas_usadas_en_registro,
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
        
        FIX BRECHA 1 (parte 2): Actualiza piezas_usadas_en_registro si se
        modifican campos de piezas dentales.
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
            
            # ===== FIX BRECHA 1 (parte 2): Actualizar trazabilidad si cambian piezas =====
            campos_pieza = any(
                field.startswith('pieza_') for field in request.data.keys()
            )
            
            if campos_pieza:
                from api.odontogram.services.piezas_service import PiezasIndiceService
                from django.utils import timezone
                
                paciente_id = str(historial.paciente_id)
                info_piezas = PiezasIndiceService.obtener_informacion_piezas(paciente_id)
                piezas_mapeo = info_piezas.get('piezas_mapeo') or info_piezas.get('piezas', {})
                
                mapeo_piezas_usadas = {}
                for pieza_original, info in piezas_mapeo.items():
                    pieza_usada = info.get('codigo_usado', pieza_original)
                    tiene_datos = False
                    datos_pieza = {}
                    
                    for campo in ['placa', 'calculo', 'gingivitis']:
                        valor = getattr(indicadores, f"pieza_{pieza_original}_{campo}", None)
                        if valor is not None:
                            tiene_datos = True
                            datos_pieza[campo] = valor
                    
                    if tiene_datos:
                        mapeo_piezas_usadas[pieza_original] = {
                            'codigo_usado': pieza_usada,
                            'es_alternativa': info.get('es_alternativa', pieza_usada != pieza_original),
                            'codigo_original': pieza_original,
                            'disponible': info.get('disponible', True),
                            'diente_id': info.get('diente_id'),
                            'ambos_ausentes': info.get('ambos_ausentes', False),
                            'datos': datos_pieza
                        }
                
                indicadores.piezas_usadas_en_registro = {
                    'piezas_mapeo': mapeo_piezas_usadas,
                    'denticion': info_piezas.get('denticion'),
                    'estadisticas': info_piezas.get('estadisticas'),
                    'fecha_registro': str(timezone.now()),
                    'tipo_operacion': 'actualizacion'
                }
                indicadores.save(update_fields=['piezas_usadas_en_registro'])
            # ===== FIN FIX =====
            
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
    
    @action(detail=False, methods=['get'], url_path='diagnosticos-cie')
    def latest_diagnosticos_cie(self, request):
        """
        Obtiene diagnósticos CIE-10 desde la base de datos para un paciente.
        """
        pacienteid = request.query_params.get('pacienteid') or request.query_params.get('paciente_id')
        tipo_carga = request.query_params.get('tipo_carga', 'nuevos')
        mostrar_inactivos = request.query_params.get('mostrar_inactivos', 'false').lower() == 'true'

        if not pacienteid:
            return Response(
                {"detail": "El parámetro 'pacienteid' es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if tipo_carga not in ['nuevos', 'todos']:
            return Response(
                {"detail": "tipo_carga debe ser 'nuevos' o 'todos'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar paciente
        from api.patients.models.paciente import Paciente
        try:
            paciente = Paciente.objects.get(id=pacienteid, activo=True)
        except Paciente.DoesNotExist:
            return Response(
                {"detail": "Paciente no encontrado o inactivo"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Usar el servicio actualizado - Asegurar que siempre retorne una lista
        try:
            diagnosticos = DiagnosticosCIEService.obtener_diagnosticos_paciente(
                str(pacienteid), tipo_carga
            )
            
            # Asegurar que diagnosticos es siempre una lista
            if diagnosticos is None:
                diagnosticos = []
            
            # logger.info(f"Obtenidos {len(diagnosticos)} diagnósticos para paciente {pacienteid}, tipo: {tipo_carga}")
            
            # Filtrar inactivos si no se solicitan
            if not mostrar_inactivos:
                diagnosticos = [d for d in diagnosticos if d.get('activo', True)]
            
            return Response({
                "success": True,
                "disponible": len(diagnosticos) > 0,
                "total": len(diagnosticos),
                "tipo_carga": tipo_carga,
                "diagnosticos": diagnosticos,
                "paciente_nombre": f"{paciente.apellidos}, {paciente.nombres}",
                "paciente_cedula": paciente.cedula_pasaporte,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error obteniendo diagnósticos CIE para paciente {pacienteid}: {str(e)}")
            return Response({
                "success": False,
                "status_code": 500,
                "message": "Error interno del servidor al obtener diagnósticos",
                "data": None,
                "errors": {
                    "detail": [str(e)]
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='cargar-diagnosticos-cie')
    def cargar_diagnosticos_cie(self, request, pk=None):
        """
        Carga diagnósticos CIE-10 al historial clínico {pk}.
        Body:
        {
            "tipo_carga": "nuevos" | "todos",
            "diagnosticos": [
                {
                    "diagnostico_dental_id": "<uuid>",
                    "tipo_cie": "PRE" | "DEF"  # opcional, por defecto PRE
                },
                ...
            ]
        }
        """
        historial = self.get_object()

        if historial.estado == 'CERRADO':
            return Response(
                {"success": False, "message": "No se pueden agregar diagnósticos a un historial cerrado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        tipo_carga = request.data.get('tipo_carga', 'nuevos')
        diagnosticos_data = request.data.get('diagnosticos', [])

        if tipo_carga not in ['nuevos', 'todos']:
            return Response(
                {"success": False, "message": "tipo_carga debe ser 'nuevos' o 'todos'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Asegurar tipo PRE por defecto cuando no venga
        for d in diagnosticos_data:
            if 'tipo_cie' not in d or not d['tipo_cie']:
                d['tipo_cie'] = 'PRE'

        resultado = DiagnosticosCIEService.cargar_diagnosticos_a_historial(
            historial_clinico=historial,
            diagnosticos_data=diagnosticos_data,
            tipo_carga=tipo_carga,
            usuario=request.user,
        )

        status_code = status.HTTP_200_OK if resultado.get('success') else status.HTTP_400_BAD_REQUEST
        return Response(resultado, status=status_code)
    
    @action(detail=True, methods=['get'], url_path='obtener-diagnosticos-cie')
    def obtener_diagnosticos_cie(self, request, pk=None):
        """
        Obtiene los diagnósticos CIE-10 cargados en este historial
        GET /api/clinical-records/{id}/obtener-diagnosticos-cie/
        """
        historial = self.get_object()
        diagnosticos = DiagnosticosCIEService.obtener_diagnosticos_historial(str(historial.id))

        if not diagnosticos and not historial.diagnosticos_cie_cargados:
            return Response(
                {
                    "success": False,
                    "message": "Este historial no tiene diagnósticos CIE-10 cargados",
                    "data": None,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "success": True,
                "message": "Diagnósticos CIE-10 del historial",
                "tipo_carga": historial.tipo_carga_diagnosticos or "nuevos",
                "total_diagnosticos": len(diagnosticos),
                "diagnosticos": diagnosticos,
            }
        )
        
    @action(detail=True, methods=['delete'], 
            url_path='eliminar-diagnosticos-cie')
    def eliminar_diagnosticos_cie(self, request, pk=None):
        """
        Elimina todos los diagnósticos CIE-10 del historial
        
        DELETE: /api/clinical-records/{id}/eliminar-diagnosticos-cie/
        """
        historial = self.get_object()
        
        # Validar que el historial no esté cerrado
        if historial.estado == 'CERRADO':
            return Response({
                'success': False,
                'message': 'No se pueden modificar diagnósticos de un historial cerrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from api.clinical_records.models import DiagnosticoCIEHistorial
            
            # Eliminar todos los diagnósticos CIE de este historial
            eliminados, _ = DiagnosticoCIEHistorial.objects.filter(
                historial_clinico=historial
            ).delete()
            
            # Actualizar tracking
            historial.diagnosticos_cie_cargados = False
            historial.tipo_carga_diagnosticos = None
            historial.save()
            
            logger.info(f"{eliminados} diagnósticos CIE eliminados del historial {pk}")
            
            return Response({
                'success': True,
                'message': f'{eliminados} diagnósticos CIE eliminados del historial',
                'eliminados': eliminados
            })
            
        except Exception as e:
            logger.error(f"Error eliminando diagnósticos CIE del historial {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error eliminando diagnósticos: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            
    @action(detail=True, methods=['delete'], 
            url_path='diagnosticos-cie/(?P<diagnostico_id>[^/]+)')
    def eliminar_diagnostico_cie(self, request, pk=None, diagnostico_id=None):
        """
        Elimina un diagnóstico CIE individual del historial
        
        DELETE: /api/clinical-records/{historial_id}/diagnosticos-cie/{diagnostico_id}/
        """
        try:
            resultado = DiagnosticosCIEService.eliminar_diagnostico_individual(
                diagnostico_cie_id=diagnostico_id,
                usuario=request.user
            )
            
            if resultado['success']:
                return Response(resultado, status=status.HTTP_200_OK)
            else:
                return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error eliminando diagnóstico CIE {diagnostico_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error eliminando diagnóstico: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['patch'], 
            url_path='diagnosticos-cie/(?P<diagnostico_id>[^/]+)/actualizar-tipo')
    def actualizar_tipo_cie(self, request, pk=None, diagnostico_id=None):
        """
        Actualiza el tipo CIE (PRE/DEF) de un diagnóstico individual
        
        PATCH: /api/clinical-records/{historial_id}/diagnosticos-cie/{diagnostico_id}/actualizar-tipo/
        Body: {"tipo_cie": "DEF"}
        """
        from api.clinical_records.serializers.diagnosticos_cie_individual_serializers import (
            DiagnosticoCIEUpdateSerializer
        )
        
        serializer = DiagnosticoCIEUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Error de validación',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            resultado = DiagnosticosCIEService.actualizar_tipo_cie_individual(
                diagnostico_cie_id=diagnostico_id,
                nuevo_tipo_cie=serializer.validated_data['tipo_cie'],
                usuario=request.user
            )
            
            if resultado['success']:
                return Response(resultado, status=status.HTTP_200_OK)
            else:
                return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error actualizando tipo CIE para {diagnostico_id}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error actualizando tipo CIE: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], 
            url_path='sincronizar-diagnosticos-cie')
    def sincronizar_diagnosticos_cie(self, request, pk=None):
        """
        Sincroniza los diagnósticos CIE de un historial
        
        POST: /api/clinical-records/{historial_id}/sincronizar-diagnosticos-cie/
        Body: {
          "diagnosticos_finales": [...],
          "tipo_carga": "nuevos"
        }
        """
        from api.clinical_records.serializers.diagnosticos_cie_individual_serializers import (
            SincronizarDiagnosticosSerializer
        )
        
        serializer = SincronizarDiagnosticosSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Error de validación',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            resultado = DiagnosticosCIEService.sincronizar_diagnosticos_historial(
                historial_id=pk,
                diagnosticos_finales=serializer.validated_data['diagnosticos_finales'],
                tipo_carga=serializer.validated_data['tipo_carga'],
                usuario=request.user
            )
            
            if resultado['success']:
                return Response(resultado, status=status.HTTP_200_OK)
            else:
                return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error sincronizando diagnósticos CIE para historial {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error sincronizando diagnósticos: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            
    @action(detail=True, methods=['post'], url_path='cambiar-tipo-cie')
    def cambiar_tipo_cie(self, request, pk=None):
        """
        Cambia el tipo CIE (PRE/DEF) de uno o más diagnósticos
        y actualiza su estado activo
        
        POST: /api/clinical-records/{id}/cambiar-tipo-cie/
        Body: {
            "diagnosticos": [
                {
                    "diagnostico_cie_id": "uuid",
                    "tipo_cie": "DEF",
                    "activo": true
                }
            ]
        }
        """
        historial = self.get_object()
        
        # Validar que el historial no esté cerrado
        if historial.estado == 'CERRADO':
            return Response({
                'success': False,
                'message': 'No se pueden modificar diagnósticos de un historial cerrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        diagnosticos_data = request.data.get('diagnosticos', [])
        
        if not diagnosticos_data:
            return Response({
                'success': False,
                'message': 'Se requiere lista de diagnósticos a modificar'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resultados = []
        actualizados = 0
        errores = 0
        
        for diag_data in diagnosticos_data:
            diagnostico_cie_id = diag_data.get('diagnostico_cie_id')
            nuevo_tipo_cie = diag_data.get('tipo_cie')
            nuevo_activo = diag_data.get('activo')
            
            if not diagnostico_cie_id:
                errores += 1
                resultados.append({
                    'diagnostico_cie_id': diagnostico_cie_id,
                    'success': False,
                    'error': 'ID requerido'
                })
                continue
            
            try:
                diagnostico = DiagnosticoCIEHistorial.objects.get(
                    id=diagnostico_cie_id,
                    historial_clinico=historial
                )
                
                # Verificar permisos
                if diagnostico.historial_clinico.id != historial.id:
                    errores += 1
                    resultados.append({
                        'diagnostico_cie_id': diagnostico_cie_id,
                        'success': False,
                        'error': 'El diagnóstico no pertenece a este historial'
                    })
                    continue
                
                # Actualizar tipo CIE si se proporciona
                if nuevo_tipo_cie:
                    if nuevo_tipo_cie not in [c[0] for c in DiagnosticoCIEHistorial.TipoCIE.choices]:
                        raise ValidationError(f"Tipo CIE inválido: {nuevo_tipo_cie}")
                    diagnostico.tipo_cie = nuevo_tipo_cie
                
                # Actualizar estado activo si se proporciona
                if nuevo_activo is not None:
                    diagnostico.activo = bool(nuevo_activo)
                
                diagnostico.actualizado_por = request.user
                diagnostico.save()
                
                actualizados += 1
                resultados.append({
                    'diagnostico_cie_id': diagnostico_cie_id,
                    'success': True,
                    'tipo_cie': diagnostico.tipo_cie,
                    'activo': diagnostico.activo,
                    'message': 'Diagnóstico actualizado'
                })
                
            except DiagnosticoCIEHistorial.DoesNotExist:
                errores += 1
                resultados.append({
                    'diagnostico_cie_id': diagnostico_cie_id,
                    'success': False,
                    'error': 'Diagnóstico no encontrado'
                })
            except ValidationError as e:
                errores += 1
                resultados.append({
                    'diagnostico_cie_id': diagnostico_cie_id,
                    'success': False,
                    'error': str(e)
                })
            except Exception as e:
                errores += 1
                resultados.append({
                    'diagnostico_cie_id': diagnostico_cie_id,
                    'success': False,
                    'error': f'Error interno: {str(e)}'
                })
        
        logger.info(
            f"Tipo CIE cambiado para {actualizados} diagnósticos en historial {pk}. "
            f"Errores: {errores}"
        )
        
        return Response({
            'success': True,
            'message': f'{actualizados} diagnósticos actualizados, {errores} errores',
            'resultados': resultados,
            'total_actualizados': actualizados,
            'total_errores': errores
        })
        
    @action(detail=True, methods=['get'], url_path='plan-tratamiento')
    def obtener_plan_tratamiento(self, request, pk=None):
        historial = self.get_object()
        
        if historial.plan_tratamiento:
            from api.odontogram.serializers.plan_tratamiento_serializers import (
                PlanTratamientoDetailSerializer
            )
            
            serializer = PlanTratamientoDetailSerializer(
                historial.plan_tratamiento,
                context={'include_sesiones': True}  
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        planes_activos = PlanTratamiento.objects.filter(
            paciente=historial.paciente,
            activo=True
        ).order_by('-fecha_creacion')
        
        if planes_activos.exists():
            serializer = PlanTratamientoDetailSerializer(
                planes_activos, 
                many=True,
                context={'include_sesiones': True}
            )
            return Response({
                "detail": "Este historial no tiene plan asociado",
                "planes_disponibles": serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response(
            {"detail": "No hay planes de tratamiento activos para este paciente"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    def _validar_puede_recargar(self, pacienteid):
        """
        Busca el historial más reciente y valida que sea BORRADOR.
        """
        ultimo_historial = ClinicalRecord.objects.filter(
            paciente_id=pacienteid,  
            activo=True
        ).order_by('-fecha_creacion').first()

        if not ultimo_historial:
            return None, None 

        if ultimo_historial.estado != 'BORRADOR':
            return None, f"El historial debe estar en BORRADOR. Actual: {ultimo_historial.estado}"

        return ultimo_historial, None
    
    # GET /api/clinical-records/planes-tratamiento?pacienteid=...&latest
    @action(detail=False, methods=['get'], url_path='planes-tratamiento')
    def latest_planes_tratamiento(self, request, pacienteid=None):
        """
        Obtiene los planes de tratamiento activos de un paciente CON SESIONES
        GET: /api/clinical-records/planes-tratamiento/?pacienteid={uuid}
        """
        pacienteid = pacienteid or request.query_params.get('pacienteid')
        if not pacienteid:
            return Response(
                {"detail": "El parámetro pacienteid es requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        historial, error = self._validar_puede_recargar(pacienteid)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        try:
            planes = (
                PlanTratamiento.objects.filter(paciente_id=pacienteid, activo=True)
                .select_related('paciente', 'creado_por')
                .prefetch_related('sesiones', 'sesiones__odontologo')
                .order_by('-fecha_creacion')
            )

            # Serializar manualmente para incluir sesiones
            from api.clinical_records.serializers.plan_tratamiento_serializers import (
                SesionTratamientoDetalleCompletoSerializer
            )
            
            planes_data = []
            for plan in planes:
                # Obtener sesiones del plan
                sesiones = plan.sesiones.filter(activo=True).order_by('numero_sesion')
                sesiones_serializer = SesionTratamientoDetalleCompletoSerializer(
                    sesiones, 
                    many=True
                )
                
                planes_data.append({
                    'id': str(plan.id),
                    'titulo': plan.titulo,
                    'notas_generales': plan.notas_generales,
                    'fecha_creacion': plan.fecha_creacion.isoformat() if plan.fecha_creacion else None,
                    'activo': plan.activo,
                    'sesiones': sesiones_serializer.data,  # ← Incluir sesiones
                    'total_sesiones': sesiones.count(),
                    'paciente_info': {
                        'id': str(plan.paciente.id),
                        'nombres': plan.paciente.nombres,
                        'apellidos': plan.paciente.apellidos,
                    } if plan.paciente else None,
                })
            
            return Response(planes_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error obteniendo planes para paciente {pacienteid}: {str(e)}")
            return Response(
                {"detail": f"Error obteniendo planes: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


    @action(detail=True, methods=['get'], url_path='sesiones-plan-tratamiento')
    def obtener_sesiones_plan(self, request, pk=None):
        """
        Obtiene las sesiones del plan de tratamiento asociado a este historial
        GET: /api/clinical-records/{id}/sesiones-plan-tratamiento/
        """
        historial = self.get_object()
        
        if not historial.plan_tratamiento:
            return Response(
                {"detail": "Este historial no tiene plan de tratamiento asociado"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Obtener sesiones del plan asociado
            sesiones = SesionTratamiento.objects.filter(
                plan_tratamiento=historial.plan_tratamiento,
                activo=True
            ).order_by('numero_sesion')
            from api.clinical_records.serializers.plan_tratamiento_serializers import SesionTratamientoDetalleCompletoSerializer
            serializer = SesionTratamientoDetalleCompletoSerializer(sesiones, many=True)

            
            return Response({
                "success": True,
                "plan_id": str(historial.plan_tratamiento.id),
                "plan_titulo": historial.plan_tratamiento.titulo,
                "sesiones": serializer.data,
                "total_sesiones": sesiones.count()
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo sesiones para historial {pk}: {str(e)}")
            return Response(
                {"detail": f"Error obteniendo sesiones: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    @action(detail=True, methods=['get'], url_path='resumen-plan-tratamiento')
    def obtener_resumen_plan_tratamiento(self, request, pk=None):
        """
        Obtiene un resumen detallado del plan de tratamiento asociado al historial
        Incluye procedimientos y prescripciones consolidadas
        """
        historial = self.get_object()
        
        if not historial.plan_tratamiento:
            return Response(
                {"detail": "Este historial no tiene plan de tratamiento asociado"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            plan = historial.plan_tratamiento
            sesiones = SesionTratamiento.objects.filter(
                plan_tratamiento=plan,
                activo=True
            ).order_by('numero_sesion')
            
            # Consolidar información
            procedimientos_consolidados = []
            prescripciones_consolidadas = []
            sesiones_detalle = []
            
            for sesion in sesiones:
                # Detalle de la sesión
                sesion_detalle = {
                    'numero_sesion': sesion.numero_sesion,
                    'fecha_programada': sesion.fecha_programada.isoformat() if sesion.fecha_programada else None,
                    'fecha_realizacion': sesion.fecha_realizacion.isoformat() if sesion.fecha_realizacion else None,
                    'estado': sesion.estado,
                    'estado_display': sesion.get_estado_display(),
                    'diagnosticos_complicaciones': sesion.diagnosticos_complicaciones or [],
                    'procedimientos': sesion.procedimientos or [],
                    'prescripciones': sesion.prescripciones or [],
                    'notas': sesion.notas,
                    'observaciones': sesion.observaciones,
                }
                sesiones_detalle.append(sesion_detalle)
                
                # Consolidar procedimientos
                if sesion.procedimientos:
                    for proc in sesion.procedimientos:
                        proc['sesion'] = sesion.numero_sesion
                        procedimientos_consolidados.append(proc)
                
                # Consolidar prescripciones
                if sesion.prescripciones:
                    for pres in sesion.prescripciones:
                        pres['sesion'] = sesion.numero_sesion
                        prescripciones_consolidadas.append(pres)
            
            # Generar texto de prescripciones
            texto_prescripciones = "PRESCRIPCIONES MÉDICAS\n"
            texto_prescripciones += "=" * 30 + "\n"
            
            if prescripciones_consolidadas:
                for i, pres in enumerate(prescripciones_consolidadas, 1):
                    texto_prescripciones += f"\n{i}. {pres.get('medicamento', 'Medicamento no especificado')}\n"
                    texto_prescripciones += f"   Dosis: {pres.get('dosis', 'No especificada')}\n"
                    texto_prescripciones += f"   Frecuencia: {pres.get('frecuencia', 'No especificada')}\n"
                    texto_prescripciones += f"   Duración: {pres.get('duracion', 'No especificada')}\n"
                    if pres.get('observaciones'):
                        texto_prescripciones += f"   Observaciones: {pres['observaciones']}\n"
                    texto_prescripciones += f"   (Sesión #{pres.get('sesion', 'N/A')})\n"
            else:
                texto_prescripciones += "\nNo hay prescripciones registradas.\n"
            
            return Response({
                'success': True,
                'plan_id': str(plan.id),
                'plan_titulo': plan.titulo,
                'plan_notas_generales': plan.notas_generales,
                'fecha_creacion': plan.fecha_creacion.isoformat(),
                'total_sesiones': len(sesiones_detalle),
                'sesiones_detalle': sesiones_detalle,
                'procedimientos_consolidados': procedimientos_consolidados,
                'prescripciones_consolidadas': prescripciones_consolidadas,
                'texto_prescripciones_completo': texto_prescripciones,
                'resumen': {
                    'total_diagnosticos': sum(len(s['diagnosticos_complicaciones']) for s in sesiones_detalle),
                    'total_procedimientos': len(procedimientos_consolidados),
                    'total_prescripciones': len(prescripciones_consolidadas),
                }
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen del plan para historial {pk}: {str(e)}")
            return Response(
                {"detail": f"Error obteniendo resumen del plan: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @action(detail=True, methods=['get'], url_path='datos-completos-plan')
    def obtener_datos_completos_plan(self, request, pk=None):
        """
        Endpoint alternativo para obtener SOLO los datos del plan de tratamiento
        de un historial específico (para lazy loading si se prefiere)
        
        GET: /api/clinical-records/{id}/datos-completos-plan/
        
        Response:
            {
                "success": true,
                "historial_id": "...",
                "tiene_plan": true,
                "plan_tratamiento": {
                    "id": "...",
                    "titulo": "...",
                    "sesiones": [...],
                    "resumen_estadistico": {...},
                    "procedimientos_consolidados": [...],
                    "prescripciones_consolidadas": [...],
                    "diagnosticos_consolidados": [...]
                }
            }
        """
        historial = self.get_object()
        
        if not historial.plan_tratamiento:
            return Response(
                {
                    "success": True,
                    "historial_id": str(historial.id),
                    "tiene_plan": False,
                    "plan_tratamiento": None,
                    "message": "Este historial no tiene plan de tratamiento asociado"
                },
                status=status.HTTP_200_OK
            )
        
        try:
            from api.clinical_records.serializers.plan_tratamiento_serializers import (
                PlanTratamientoCompletoSerializer
            )
            
            serializer = PlanTratamientoCompletoSerializer(
                historial.plan_tratamiento,
                context={'request': request}
            )
            
            return Response(
                {
                    "success": True,
                    "historial_id": str(historial.id),
                    "tiene_plan": True,
                    "plan_tratamiento": serializer.data
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(
                f"Error obteniendo plan completo para historial {pk}: {str(e)}"
            )
            return Response(
                {
                    "success": False,
                    "historial_id": str(historial.id),
                    "message": f"Error obteniendo datos del plan: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    @action(
        detail=False,
        methods=['get'],
        url_path=r'examenes-complementarios/(?P<paciente_id>[^/]+)/latest',
    )
    def latest_examenes_complementarios(self, request, paciente_id=None):
        """
        Obtiene los exámenes complementarios más recientes del paciente.
        Endpoint de recarga/refresh para el formulario del historial.

        GET: /api/clinical-records/examenes-complementarios/{paciente_id}/latest/

        Respuesta exitosa:
        {
            "id": "uuid",
            "pedido_examenes": "SI",
            "pedido_examenes_detalle": "...",
            "informe_examenes": "BIOMETRIA",
            "informe_examenes_detalle": "...",
            "estado_examenes": "completado",
            ...
        }
        """
        historial, error = self._validar_puede_recargar(paciente_id)
        if error:
            return Response(
                {'detail': error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar último examen complementario del paciente
        instancia = (
            ExamenesComplementariosLinkService
            .obtener_ultimo_examen_paciente(paciente_id)
        )

        if not instancia:
            return Response(
                {
                    'detail': 'No hay exámenes complementarios previos',
                    'disponible': False,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WritableExamenesComplementariosSerializer(instancia)
        return Response(serializer.data)


    # ================================================================
    # EXÁMENES COMPLEMENTARIOS - OBTENER (LECTURA DESDE HISTORIAL)
    # ================================================================

    @action(
        detail=True,
        methods=['get'],
        url_path='examenes-complementarios',
    )
    def obtener_examenes_complementarios(self, request, pk=None):
        """
        Obtiene los exámenes complementarios asociados a este historial.

        GET: /api/clinical-records/{id}/examenes-complementarios/

        Respuesta:
        {
            "success": true,
            "message": "...",
            "data": { ...serialized examenes... },
            "source": "historial_fk" | "paciente_latest"
        }
        """
        historial = self.get_object()

        # 1) Buscar por FK directa en el historial
        if historial.examenes_complementarios:
            serializer = WritableExamenesComplementariosSerializer(
                historial.examenes_complementarios
            )
            return Response({
                'success': True,
                'message': 'Exámenes complementarios del historial',
                'data': serializer.data,
                'source': 'historial_fk',
            })

        # 2) Fallback: buscar el más reciente del paciente
        instancia = (
            ExamenesComplementariosLinkService
            .obtener_ultimo_examen_paciente(str(historial.paciente_id))
        )

        if instancia:
            serializer = WritableExamenesComplementariosSerializer(instancia)
            return Response({
                'success': True,
                'message': (
                    'Exámenes complementarios más recientes del paciente '
                    '(no asociados a este historial)'
                ),
                'data': serializer.data,
                'source': 'paciente_latest',
                'warning': (
                    'Este historial no tiene exámenes complementarios '
                    'asociados específicamente'
                ),
            })

        return Response(
            {
                'success': False,
                'message': (
                    'No hay exámenes complementarios para este historial '
                    'ni para el paciente'
                ),
                'data': None,
            },
            status=status.HTTP_404_NOT_FOUND,
        )


    # ================================================================
    # EXÁMENES COMPLEMENTARIOS - GUARDAR (CREAR Y VINCULAR)
    # ================================================================

    @action(
        detail=True,
        methods=['post'],
        url_path='guardar-examenes-complementarios',
    )
    def guardar_examenes_complementarios(self, request, pk=None):
        """
        Crea nuevos exámenes complementarios y los asocia al historial.

        POST: /api/clinical-records/{id}/guardar-examenes-complementarios/
        Body:
        {
            "pedido_examenes": "SI",
            "pedido_examenes_detalle": "Radiografía panorámica, hemograma completo",
            "informe_examenes": "NINGUNO",
            "informe_examenes_detalle": ""
        }

        También acepta vincular un examen existente:
        {
            "examenes_complementarios_id": "<uuid>"
        }
        """
        historial = self.get_object()

        # Validar que el historial no esté cerrado
        if historial.estado == 'CERRADO':
            return Response(
                {
                    'success': False,
                    'message': (
                        'No se pueden agregar exámenes complementarios '
                        'a un historial cerrado'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Opción A: Vincular examen existente por ID
            examenes_id = request.data.get('examenes_complementarios_id')
            if examenes_id:
                try:
                    examen = ExamenesComplementarios.objects.get(
                        id=examenes_id,
                        paciente=historial.paciente,
                        activo=True,
                    )
                    historial.examenes_complementarios = examen
                    historial.save(
                        update_fields=['examenes_complementarios']
                    )

                    logger.info(
                        f"Exámenes {examen.id} asociados al historial {pk}"
                    )

                    return Response(
                        {
                            'success': True,
                            'message': 'Exámenes asociados exitosamente',
                            'data': WritableExamenesComplementariosSerializer(
                                examen
                            ).data,
                        },
                        status=status.HTTP_200_OK,
                    )
                except ExamenesComplementarios.DoesNotExist:
                    return Response(
                        {
                            'detail': (
                                'Los exámenes especificados no existen '
                                'o no pertenecen al paciente'
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Opción B: Crear nuevos exámenes
            data = request.data.copy()
            data['paciente'] = str(historial.paciente_id)

            serializer = WritableExamenesComplementariosSerializer(data=data)
            serializer.is_valid(raise_exception=True)

            examen = ExamenesComplementarios.objects.create(
                paciente=historial.paciente,
                creado_por=request.user,
                **{
                    k: v
                    for k, v in serializer.validated_data.items()
                    if k != 'paciente'
                },
            )

            # Vincular al historial
            historial.examenes_complementarios = examen
            historial.save(update_fields=['examenes_complementarios'])

            logger.info(
                f"Exámenes {examen.id} creados y asociados "
                f"al historial {pk} por {request.user.username}"
            )

            return Response(
                {
                    'success': True,
                    'message': (
                        'Exámenes complementarios creados y asociados '
                        'al historial exitosamente'
                    ),
                    'data': WritableExamenesComplementariosSerializer(
                        examen
                    ).data,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            logger.error(
                f"Error validando exámenes para historial {pk}: {str(e)}"
            )
            return Response(
                {
                    'success': False,
                    'message': 'Error de validación',
                    'errors': e.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.error(
                f"Error guardando exámenes para historial {pk}: {str(e)}"
            )
            return Response(
                {
                    'success': False,
                    'message': f'Error guardando exámenes: {str(e)}',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ================================================================
    # EXÁMENES COMPLEMENTARIOS - ACTUALIZAR
    # ================================================================

    @action(
        detail=True,
        methods=['patch'],
        url_path='actualizar-examenes-complementarios',
    )
    def actualizar_examenes_complementarios(self, request, pk=None):
        """
        Actualiza los exámenes complementarios asociados al historial.

        PATCH: /api/clinical-records/{id}/actualizar-examenes-complementarios/
        Body (parcial):
        {
            "informe_examenes": "BIOMETRIA",
            "informe_examenes_detalle": "Resultados normales..."
        }
        """
        historial = self.get_object()

        # Validar que el historial no esté cerrado
        if historial.estado == 'CERRADO':
            return Response(
                {'detail': 'No se puede modificar un historial cerrado'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verificar que el historial tenga exámenes asociados
        if not historial.examenes_complementarios:
            return Response(
                {
                    'detail': (
                        'Este historial no tiene exámenes complementarios '
                        'asociados. Use guardar-examenes-complementarios '
                        'para crear nuevos.'
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WritableExamenesComplementariosSerializer(
            historial.examenes_complementarios,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            examen = serializer.save()

            logger.info(
                f"Exámenes {examen.id} actualizados "
                f"para historial {pk} por {request.user.username}"
            )

            return Response(
                {
                    'success': True,
                    'message': 'Exámenes complementarios actualizados exitosamente',
                    'data': WritableExamenesComplementariosSerializer(
                        examen
                    ).data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(
                f"Error actualizando exámenes para historial {pk}: {str(e)}"
            )
            return Response(
                {
                    'detail': f'Error al actualizar exámenes: {str(e)}',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


    # ================================================================
    # EXÁMENES COMPLEMENTARIOS - HISTORIAL COMPLETO DEL PACIENTE
    # ================================================================

    @action(
        detail=True,
        methods=['get'],
        url_path='todos-examenes-complementarios',
    )
    def todos_examenes_complementarios(self, request, pk=None):
        """
        Obtiene TODOS los exámenes complementarios del paciente
        del historial (para ver historial completo de exámenes).

        GET: /api/clinical-records/{id}/todos-examenes-complementarios/
        """
        historial = self.get_object()

        examenes = (
            ExamenesComplementariosLinkService
            .obtener_todos_examenes_paciente(str(historial.paciente_id))
        )

        serializer = WritableExamenesComplementariosSerializer(
            examenes, many=True
        )

        return Response({
            'success': True,
            'total': examenes.count(),
            'paciente_id': str(historial.paciente_id),
            'examenes': serializer.data,
        })
        
    def destroy(self, request, *args, **kwargs):
        """Eliminación lógica del historial"""
        instance = self.get_object()
        
        # Validar que no esté cerrado
        if instance.estado == 'CERRADO':
            return Response(
                {'detail': 'No se puede eliminar un historial cerrado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Eliminación lógica
        ClinicalRecordService.eliminar_historial(str(instance.id))
        
        # Refrescar para obtener el estado actualizado (activo=False)
        instance.refresh_from_db()
        
        # Usar el método del mixin
        self.log_delete(instance, request.user)
        
        return Response(
            {
                'success': True,
                'message': 'Historial eliminado correctamente',
                'id': str(instance.id)
            },
            status=status.HTTP_200_OK
        )