# api/patients/views.py

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError

from api.patients.models.paciente import Paciente
from api.patients.serializers import AntecedentesFamiliaresSerializer, AntecedentesPersonalesSerializer, ConstantesVitalesSerializer, ExamenEstomatognaticoSerializer, PacienteSerializer
from api.patients.services.patient_service import PatientService
from api.patients.models.antecedentes_personales import AntecedentesPersonales
from api.patients.models.antecedentes_familiares import AntecedentesFamiliares
from api.patients.models.constantes_vitales import ConstantesVitales
from api.patients.models.examen_estomatognatico import ExamenEstomatognatico
from api.users.permissions import UserBasedPermission

import logging




logger = logging.getLogger(__name__)


class PacientePagination(PageNumberPagination):
    """Configuración de paginación para pacientes"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PacienteViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de pacientes"""
    serializer_class = PacienteSerializer
    queryset = Paciente.objects.all()
    permission_classes = [IsAuthenticated, UserBasedPermission]
    permission_model_name = "paciente"
    pagination_class = PacientePagination

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['sexo', 'activo', 'condicion_edad']
    ordering_fields = ['apellidos', 'nombres', 'fecha_creacion', 'edad']
    ordering = ['apellidos', 'nombres']

    def get_queryset(self):
        """Queryset base con filtros y búsqueda"""
        request = self.request
        search = (request.query_params.get("search") or "").strip()
        activo_param = request.query_params.get("activo")
        
        qs = Paciente.objects.select_related(
            "creado_por",
            "actualizado_por"
        ).order_by('apellidos', 'nombres')
        
        # Filtrar por estado
        if activo_param is not None:
            activo = activo_param.lower() == 'true'
            qs = qs.filter(activo=activo)
     
        # Búsqueda manual (más flexible que search_fields)
        if search:
            qs = qs.filter(
                Q(nombres__icontains=search)
                | Q(apellidos__icontains=search)
                | Q(cedula_pasaporte__icontains=search)
                | Q(telefono__icontains=search)
                | Q(correo__icontains=search)
            )
        
        return qs

    def create(self, request, *args, **kwargs):
        """Crear nuevo paciente"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        paciente = PatientService.crear_paciente(serializer.validated_data)
        output_serializer = self.get_serializer(paciente)
        
        logger.info(f"Paciente {paciente.nombres} {paciente.apellidos} creado por {request.user.username}")
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Actualizar paciente"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        paciente = PatientService.actualizar_paciente(instance, serializer.validated_data)
        output_serializer = self.get_serializer(paciente)
        
        logger.info(f"Paciente {paciente.id} actualizado por {request.user.username}")
        return Response(output_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Eliminación lógica del paciente"""
        instance = self.get_object()
        PatientService.eliminar_paciente(instance)
        
        logger.info(f"Paciente {instance.id} desactivado por {request.user.username}")
        return Response({'id': str(instance.id)})




class AntecedentesPersonalesViewSet(viewsets.ModelViewSet):
    """ViewSet para antecedentes personales"""
    serializer_class = AntecedentesPersonalesSerializer
    queryset = AntecedentesPersonales.objects.all()
    permission_classes = [IsAuthenticated, UserBasedPermission]
    permission_model_name = "paciente"
    pagination_class = PacientePagination
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['paciente', 'activo']
    ordering_fields = ['fecha_creacion', 'fecha_modificacion']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        """Queryset base con filtros y búsqueda"""
        request = self.request
        search = (request.query_params.get("search") or "").strip()
        activo_param = request.query_params.get("activo")
        
        qs = AntecedentesPersonales.objects.select_related('paciente').order_by('-fecha_creacion')
        
        # Filtrar por estado
        if activo_param is not None:
            activo = activo_param.lower() == 'true'
            qs = qs.filter(activo=activo)
        
        # Búsqueda en datos del paciente
        if search:
            qs = qs.filter(
                Q(paciente__nombres__icontains=search)
                | Q(paciente__apellidos__icontains=search)
                | Q(paciente__cedula_pasaporte__icontains=search)
            )
        
        return qs

    def create(self, request, *args, **kwargs):
        """Crear antecedentes personales"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Verificar duplicados
        paciente_id = serializer.validated_data.get('paciente')
        if AntecedentesPersonales.objects.filter(paciente=paciente_id, activo=True).exists():
            raise ValidationError({'detail': 'Este paciente ya tiene antecedentes personales registrados'})
        
        self.perform_create(serializer)
        logger.info(f"Antecedentes creados para paciente {paciente_id} por {request.user.username}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Actualizar antecedentes"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        self.perform_update(serializer)
        logger.info(f"Antecedentes {instance.id} actualizados por {request.user.username}")
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Eliminación lógica"""
        instance = self.get_object()
        instance.activo = False
        instance.save()
        
        logger.info(f"Antecedentes {instance.id} desactivados por {request.user.username}")
        return Response({'id': str(instance.id)})

    @action(detail=False, methods=['get'], url_path='by-paciente/(?P<paciente_id>[^/.]+)')
    def by_paciente(self, request, paciente_id=None):
        """Obtener antecedentes por ID de paciente"""
        try:
            antecedentes = AntecedentesPersonales.objects.get(
                paciente_id=paciente_id,
                activo=True
            )
            serializer = self.get_serializer(antecedentes)
            return Response(serializer.data)
        except AntecedentesPersonales.DoesNotExist:
            raise ValidationError({'detail': 'No se encontraron antecedentes para este paciente'})



# ============================================================================
# ✅ NUEVO: VIEWSET ANTECEDENTES FAMILIARES
# ============================================================================

class AntecedentesFamiliaresViewSet(viewsets.ModelViewSet):
    """ViewSet para antecedentes familiares"""
    serializer_class = AntecedentesFamiliaresSerializer
    queryset = AntecedentesFamiliares.objects.all()
    permission_classes = [IsAuthenticated, UserBasedPermission]
    permission_model_name = "paciente"
    pagination_class = PacientePagination
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['paciente', 'activo']
    ordering_fields = ['fecha_creacion', 'fecha_modificacion']
    ordering = ['-fecha_creacion']


    def get_queryset(self):
        """Queryset base con filtros y búsqueda"""
        request = self.request
        search = (request.query_params.get("search") or "").strip()
        activo_param = request.query_params.get("activo")
        
        qs = AntecedentesFamiliares.objects.select_related('paciente').order_by('-fecha_creacion')
        
        # Filtrar por estado
        if activo_param is not None:
            activo = activo_param.lower() == 'true'
            qs = qs.filter(activo=activo)
        
        # Búsqueda en datos del paciente
        if search:
            qs = qs.filter(
                Q(paciente__nombres__icontains=search)
                | Q(paciente__apellidos__icontains=search)
                | Q(paciente__cedula_pasaporte__icontains=search)
            )
        
        return qs


    def create(self, request, *args, **kwargs):
        """Crear antecedentes familiares"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Verificar duplicados
        paciente_id = serializer.validated_data.get('paciente')
        if AntecedentesFamiliares.objects.filter(paciente=paciente_id, activo=True).exists():
            raise ValidationError({'detail': 'Este paciente ya tiene antecedentes familiares registrados'})
        
        self.perform_create(serializer)
        logger.info(f"Antecedentes familiares creados para paciente {paciente_id} por {request.user.username}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)


    def update(self, request, *args, **kwargs):
        """Actualizar antecedentes familiares"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        self.perform_update(serializer)
        logger.info(f"Antecedentes familiares {instance.id} actualizados por {request.user.username}")
        return Response(serializer.data)


    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


    def destroy(self, request, *args, **kwargs):
        """Eliminación lógica"""
        instance = self.get_object()
        instance.activo = False
        instance.save()
        
        logger.info(f"Antecedentes familiares {instance.id} desactivados por {request.user.username}")
        return Response({'id': str(instance.id)})


    @action(detail=False, methods=['get'], url_path='by-paciente/(?P<paciente_id>[^/.]+)')
    def by_paciente(self, request, paciente_id=None):
        """Obtener antecedentes familiares por ID de paciente"""
        try:
            antecedentes = AntecedentesFamiliares.objects.get(
                paciente_id=paciente_id,
                activo=True
            )
            serializer = self.get_serializer(antecedentes)
            return Response(serializer.data)
        except AntecedentesFamiliares.DoesNotExist:
            raise ValidationError({'detail': 'No se encontraron antecedentes familiares para este paciente'})
        



# ============================================================================
# ✅ NUEVO: VIEWSET CONSTANTES VITALES
# ============================================================================

class ConstantesVitalesViewSet(viewsets.ModelViewSet):
    """ViewSet para constantes vitales"""
    serializer_class = ConstantesVitalesSerializer
    queryset = ConstantesVitales.objects.all()
    permission_classes = [IsAuthenticated, UserBasedPermission]
    permission_model_name = "paciente"
    pagination_class = PacientePagination
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['paciente', 'activo']
    ordering_fields = ['fecha_creacion', 'fecha_modificacion']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        """Queryset base con filtros y búsqueda"""
        request = self.request
        search = (request.query_params.get("search") or "").strip()
        activo_param = request.query_params.get("activo")
        
        qs = ConstantesVitales.objects.select_related('paciente').order_by('-fecha_creacion')
        
        # Filtrar por estado
        if activo_param is not None:
            activo = activo_param.lower() == 'true'
            qs = qs.filter(activo=activo)
        
        # Búsqueda en datos del paciente
        if search:
            qs = qs.filter(
                Q(paciente__nombres__icontains=search)
                | Q(paciente__apellidos__icontains=search)
                | Q(paciente__cedula_pasaporte__icontains=search)
            )
        
        return qs

    def create(self, request, *args, **kwargs):
        """Crear constantes vitales"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Verificar duplicados
        paciente_id = serializer.validated_data.get('paciente')
        if ConstantesVitales.objects.filter(paciente=paciente_id, activo=True).exists():
            raise ValidationError({'detail': 'Este paciente ya tiene constantes vitales registradas'})
        
        self.perform_create(serializer)
        logger.info(f"Constantes vitales creadas para paciente {paciente_id} por {request.user.username}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Actualizar constantes vitales"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        self.perform_update(serializer)
        logger.info(f"Constantes vitales {instance.id} actualizadas por {request.user.username}")
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Eliminación lógica"""
        instance = self.get_object()
        instance.activo = False
        instance.save()
        
        logger.info(f"Constantes vitales {instance.id} desactivadas por {request.user.username}")
        return Response({'id': str(instance.id)})

    @action(detail=False, methods=['get'], url_path='by-paciente/(?P<paciente_id>[^/.]+)')
    def by_paciente(self, request, paciente_id=None):
        """Obtener constantes vitales por ID de paciente"""
        try:
            constantes = ConstantesVitales.objects.get(
                paciente_id=paciente_id,
                activo=True
            )
            serializer = self.get_serializer(constantes)
            return Response(serializer.data)
        except ConstantesVitales.DoesNotExist:
            raise ValidationError({'detail': 'No se encontraron constantes vitales para este paciente'})




class ExamenEstomatognaticoViewSet(viewsets.ModelViewSet):
    """ViewSet para examen estomatognático"""
    serializer_class = ExamenEstomatognaticoSerializer
    queryset = ExamenEstomatognatico.objects.all()
    permission_classes = [IsAuthenticated, UserBasedPermission]
    permission_model_name = "paciente"
    pagination_class = PacientePagination
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['paciente', 'activo', 'examen_sin_patologia']
    ordering_fields = ['fecha_creacion', 'fecha_modificacion']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        """Queryset base con filtros y búsqueda"""
        request = self.request
        search = (request.query_params.get("search") or "").strip()
        activo_param = request.query_params.get("activo")
        
        qs = ExamenEstomatognatico.objects.select_related('paciente').order_by('-fecha_creacion')
        
        # Filtrar por estado
        if activo_param is not None:
            activo = activo_param.lower() == 'true'
            qs = qs.filter(activo=activo)
        
        # Búsqueda en datos del paciente
        if search:
            qs = qs.filter(
                Q(paciente__nombres__icontains=search)
                | Q(paciente__apellidos__icontains=search)
                | Q(paciente__cedula_pasaporte__icontains=search)
            )
        
        return qs

    def create(self, request, *args, **kwargs):
        """Crear examen estomatognático"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Verificar duplicados
        paciente_id = serializer.validated_data.get('paciente')
        if ExamenEstomatognatico.objects.filter(paciente=paciente_id, activo=True).exists():
            raise ValidationError({'detail': 'Este paciente ya tiene examen estomatognático registrado'})
        
        self.perform_create(serializer)
        logger.info(f"Examen estomatognático creado para paciente {paciente_id} por {request.user.username}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Actualizar examen estomatognático"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        self.perform_update(serializer)
        logger.info(f"Examen estomatognático {instance.id} actualizado por {request.user.username}")
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Eliminación lógica"""
        instance = self.get_object()
        instance.activo = False
        instance.save()
        
        logger.info(f"Examen estomatognático {instance.id} desactivado por {request.user.username}")
        return Response({'id': str(instance.id)})

    @action(detail=False, methods=['get'], url_path='by-paciente/(?P<paciente_id>[^/.]+)')
    def by_paciente(self, request, paciente_id=None):
        """Obtener examen estomatognático por ID de paciente"""
        try:
            examen = ExamenEstomatognatico.objects.get(
                paciente_id=paciente_id,
                activo=True
            )
            serializer = self.get_serializer(examen)
            return Response(serializer.data)
        except ExamenEstomatognatico.DoesNotExist:
            raise ValidationError({'detail': 'No se encontró examen estomatognático para este paciente'})

    @action(detail=True, methods=['get'])
    def resumen_patologias(self, request, pk=None):
        """Resumen de patologías encontradas"""
        instance = self.get_object()
        data = {
            'tiene_patologias': instance.tiene_patologias,
            'examen_sin_patologia': instance.examen_sin_patologia,
            'regiones_con_patologia': instance.regiones_con_patologia,
            'atm_patologias': instance.atm_patologias,
            'total_regiones_anormales': len(instance.regiones_con_patologia)
        }
        return Response(data)