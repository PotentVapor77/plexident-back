# odontogram/views.py
"""
Views refactorizadas para estructura alineada
Separa: Catálogo (ViewSets lectura) + Instancias (ViewSets CRUD)
"""

import logging
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.db.models import Q, Prefetch

from api.odontogram.models import (
    # Catálogo
    CategoriaDiagnostico,
    Diagnostico,
    AreaAfectada,
    TipoAtributoClinico,
    OpcionAtributoClinico,
    # Instancias
    Paciente,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma,
)
from api.odontogram.serializers import (
    # Catálogo
    CategoriaDiagnosticoSerializer,
    DiagnosticoListSerializer,
    DiagnosticoDetailSerializer,
    AreaAfectadaSerializer,
    TipoAtributoClinicoSerializer,
    OdontogramaConfigSerializer,
    # Instancias
    PacienteBasicSerializer,
    PacienteDetailSerializer,
    DienteDetailSerializer,
    SuperficieDentalListSerializer,
    DiagnosticoDentalListSerializer,
    DiagnosticoDentalDetailSerializer,
    DiagnosticoDentalCreateSerializer,
    HistorialOdontogramaSerializer,
)
from api.odontogram.services.odontogram_services import OdontogramaService
from api.odontogram.repositories.odontogram_repositories import (
    CategoriaDiagnosticoRepository,
    DiagnosticoRepository,
    AreaAfectadaRepository,
    TipoAtributoClinicoRepository,
)

# =============================================================================
# VIEWSETS PARA CATÁLOGO (Solo lectura)
# =============================================================================


logger = logging.getLogger(__name__)

class CategoriaDiagnosticoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para categorías de diagnóstico (catálogo)"""
    serializer_class = CategoriaDiagnosticoSerializer
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repository = CategoriaDiagnosticoRepository()

    def get_queryset(self):
        return self.repository.get_with_diagnosticos()

    @action(detail=False, methods=['get'])
    def por_prioridad(self, request):
        """GET /api/catalogo/categorias/por_prioridad/?prioridad=ALTA"""
        prioridad_key = request.query_params.get('prioridad')
        if not prioridad_key:
            return Response(
                {'error': 'Se requiere el parámetro prioridad'},
                status=status.HTTP_400_BAD_REQUEST
            )
        categorias = self.repository.get_by_prioridad(prioridad_key)
        serializer = self.get_serializer(categorias, many=True)
        return Response(serializer.data)


class DiagnosticoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para diagnósticos del catálogo"""
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repository = DiagnosticoRepository()

    def get_queryset(self):
        return self.repository.get_all().select_related('categoria')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DiagnosticoDetailSerializer
        return DiagnosticoListSerializer

    def retrieve(self, request, pk=None):
        """GET /api/catalogo/diagnosticos/{id}/ con caché"""
        cache_key = f'odontograma:diagnostico:{pk}'
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        diagnostico_data = self.repository.get_by_id(int(pk))
        if not diagnostico_data:
            return Response(
                {'error': 'Diagnóstico no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(diagnostico_data)
        cache.set(cache_key, serializer.data, timeout=3600)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_categoria(self, request):
        """GET /api/catalogo/diagnosticos/por_categoria/?categoria_id=1"""
        categoria_id = request.query_params.get('categoria_id')
        if not categoria_id:
            return Response(
                {'error': 'Se requiere el parámetro categoria_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        diagnosticos = self.repository.get_by_categoria(int(categoria_id))
        serializer = self.get_serializer(diagnosticos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def criticos(self, request):
        """GET /api/catalogo/diagnosticos/criticos/"""
        diagnosticos = self.repository.get_criticos()
        serializer = self.get_serializer(diagnosticos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """GET /api/catalogo/diagnosticos/buscar/?q=caries"""
        query = request.query_params.get('q')
        if not query:
            return Response(
                {'error': 'Se requiere el parámetro q'},
                status=status.HTTP_400_BAD_REQUEST
            )
        diagnosticos = self.repository.search(query)
        serializer = self.get_serializer(diagnosticos, many=True)
        return Response(serializer.data)


class AreaAfectadaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para áreas afectadas"""
    serializer_class = AreaAfectadaSerializer
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repository = AreaAfectadaRepository()

    def get_queryset(self):
        return self.repository.get_all()


class TipoAtributoClinicoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para tipos de atributos clínicos"""
    serializer_class = TipoAtributoClinicoSerializer
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repository = TipoAtributoClinicoRepository()

    def get_queryset(self):
        return self.repository.get_with_opciones()


class OdontogramaConfigViewSet(viewsets.ViewSet):
    """ViewSet para obtener configuración completa del odontograma"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def config(self, request):
        """GET /api/catalogo/config/ - Configuración completa con caché"""
        cache_key = 'odontograma:config:full'
        cached_config = cache.get(cache_key)

        if cached_config:
            return Response(cached_config)

        from api.odontogram.services.odontogram_services import OdontogramaService
        service = OdontogramaService()
        config = service.get_full_config()

        serializer = OdontogramaConfigSerializer(config)
        cache.set(cache_key, serializer.data, timeout=3600)
        return Response(serializer.data)

# =============================================================================
# VIEWSETS PARA INSTANCIAS (CRUD)
# =============================================================================

class PacienteViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar pacientes"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Paciente.objects.filter(activo=True)

        # Filtro por búsqueda
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombres__icontains=search) |
                Q(apellidos__icontains=search) |
                Q(cedula__icontains=search)
            )

        return queryset.prefetch_related('dientes')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PacienteDetailSerializer
        return PacienteBasicSerializer

    @action(detail=True, methods=['get'])
    def odontograma(self, request, pk=None):
        """GET /api/pacientes/{id}/odontograma/ - Odontograma completo"""
        paciente = self.get_object()
        service = OdontogramaService()
        odontograma = service.obtener_odontograma_completo(str(paciente.id))
        return Response(odontograma)

    @action(detail=True, methods=['get'])
    def diagnosticos(self, request, pk=None):
        """GET /api/pacientes/{id}/diagnosticos/ - Todos los diagnósticos"""
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
        Retorna el odontograma completo del paciente como un Bundle FHIR.
        """
        # Importaciones necesarias para esta acción
        import uuid
        from django.utils import timezone
        from api.odontogram.serializer.fhir_serializers import ClinicalFindingFHIRSerializer

        paciente = self.get_object()
        
        # 1. Obtener todos los hallazgos clínicos del paciente
        diagnosticos_qs = DiagnosticoDental.objects.filter(
            superficie__diente__paciente=paciente,
            activo=True
        ).select_related(
            'diagnostico_catalogo',
            'superficie__diente__paciente',
            'odontologo'
        )

        # 2. Serializar los hallazgos a recursos FHIR (Condition/Procedure)
        fhir_findings = ClinicalFindingFHIRSerializer(diagnosticos_qs, many=True).data

        # 3. Construir el Bundle FHIR
        bundle_entries = []
        
        # 3.1. Añadir el recurso del Paciente (una versión más completa que la de referencia)
        patient_resource = {
            "fullUrl": f"urn:uuid:{paciente.id}",
            "resource": {
                "resourceType": "Patient",
                "id": str(paciente.id),
                "name": [{
                    "use": "official",
                    "family": paciente.apellidos,
                    "given": [paciente.nombres]
                }],
                "identifier": [{
                    "system": "urn:oid:1.3.6.1.4.1.21367.13.20.3000.1.1", # OID de ejemplo para Cédula Ecuador
                    "value": paciente.cedula_pasaporte
                }],
                "gender": {"M": "male", "F": "female", "O": "other"}.get(paciente.sexo),
                "birthDate": paciente.fecha_nacimiento.isoformat(),
            }
        }
        bundle_entries.append(patient_resource)
        
        # 3.2. Añadir recursos de Practitioner (odontólogos) únicos
        practitioners = {d.odontologo for d in diagnosticos_qs if d.odontologo}
        for pract in practitioners:
            bundle_entries.append({
                "fullUrl": f"urn:uuid:{pract.id}",
                "resource": {
                    "resourceType": "Practitioner",
                    "id": str(pract.id),
                    "name": [{"family": pract.last_name, "given": [pract.first_name]}]
                }
            })

        # 3.3. Añadir cada hallazgo clínico al bundle
        for finding in fhir_findings:
            bundle_entries.append({
                "fullUrl": f"urn:uuid:{finding['id']}",
                "resource": finding
            })

        # 4. Ensamblar el Bundle final
        fhir_bundle = {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "type": "document",
            "timestamp": timezone.now().isoformat(),
            "entry": bundle_entries
        }

        return Response(fhir_bundle, status=status.HTTP_200_OK)


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
        """POST /api/dientes/{id}/marcar_ausente/"""
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
        queryset = DiagnosticoDental.objects.filter(activo=True)

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
        """POST /api/diagnosticos-aplicados/{id}/marcar_tratado/"""
        from django.utils import timezone

        diagnostico = self.get_object()
        diagnostico.estado_tratamiento = DiagnosticoDental.EstadoTratamiento.TRATADO
        diagnostico.fecha_tratamiento = timezone.now()
        diagnostico.save()

        serializer = self.get_serializer(diagnostico)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'])
    def eliminar(self, request, pk=None):
        """DELETE /api/diagnosticos-aplicados/{id}/eliminar/"""
        diagnostico = self.get_object()
        service = OdontogramaService()

        odontologo_id = request.user.id
        resultado = service.eliminar_diagnostico(str(diagnostico.id), odontologo_id)

        if resultado:
            return Response({'success': True})
        return Response({'error': 'No se pudo eliminar'}, status=status.HTTP_400_BAD_REQUEST)


class HistorialOdontogramaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consultar historial del odontograma"""
    serializer_class = HistorialOdontogramaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        diente_id = self.request.query_params.get('diente_id')
        paciente_id = self.request.query_params.get('paciente_id')

        queryset = HistorialOdontograma.objects.all()

        if diente_id:
            queryset = queryset.filter(diente_id=diente_id)
        elif paciente_id:
            queryset = queryset.filter(diente__paciente_id=paciente_id)

        return queryset.select_related('odontologo', 'diente')