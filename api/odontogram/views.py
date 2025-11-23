# odontogram/views.py
"""
Views refactorizadas para estructura alineada
Separa: Catálogo (ViewSets lectura) + Instancias (ViewSets CRUD)
"""

import logging
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
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
from api.odontogram.generators.cda_generador import CDAOdontogramGenerator
from api.odontogram.serializers.fhir_serializers import ClinicalFindingFHIRSerializer
from api.odontogram.serializers.bundle_serializers import FHIRBundleSerializer
from api.odontogram.serializers.serializers import DienteSerializer
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

class OdontogramaViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def por_paciente(self, request):
        """
        GET /api/odontograma/por_paciente/?paciente_id={id}
        Retorna todos los dientes con diagnósticos del paciente
        Estructura esperada por frontend 3D
        """
        paciente_id = request.query_params.get('paciente_id')
        if not paciente_id:
            return Response(
                {'error': 'paciente_id requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        paciente = get_object_or_404(Paciente, id=paciente_id)
        
        dientes = Diente.objects.filter(paciente=paciente).prefetch_related(
            'superficies__diagnosticos__diagnostico_catalogo'
        )
        
        serializer = DienteSerializer(dientes, many=True)
        
        # Transformar a estructura {codigo_fdi: {...}}
        odontograma = {}
        for diente_data in serializer.data:
            codigo_fdi = diente_data['codigo_fdi']
            odontograma[codigo_fdi] = diente_data
        
        return Response({
            'paciente_id': str(paciente.id),
            'dientes': odontograma
        })
        
    @action(detail=False, methods=['get'])
    def por_codigo_fdi(self, request):
        """
        GET /api/odontograma/por_codigo_fdi/?paciente_id={id}&codigo_fdi={fdi}
        Obtiene un diente específico por su código FDI
        """
        paciente_id = request.query_params.get('paciente_id')
        codigo_fdi = request.query_params.get('codigo_fdi')
        
        if not paciente_id or not codigo_fdi:
            return Response(
                {'error': 'paciente_id y codigo_fdi requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        diente = get_object_or_404(
            Diente,
            paciente_id=paciente_id,
            codigo_fdi=codigo_fdi
        )
        
        serializer = DienteSerializer(diente)
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
    
    
    
# Exportadores FHIR
# -----------------------------------------------
@api_view(['GET'])
def export_fhir_bundle(request, paciente_id):
    """
    Exporta el odontograma completo como Bundle FHIR R4.
    
    Endpoint: GET /api/odontogramas/{paciente_id}/export-fhir-bundle/
    
    Response: JSON con Bundle FHIR conteniendo:
    - Patient resource
    - BodyStructure resources (superficies)
    - Observation/Condition/Procedure resources (diagnósticos)
    """
    
    try:
        paciente = Paciente.objects.get(id=paciente_id)
    except Paciente.DoesNotExist:
        return Response(
            {'error': 'Paciente no encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = FHIRBundleSerializer(paciente)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def export_cda_xml(request, paciente_id):
    """
    Exporta el odontograma como documento CDA v3 XML.
    
    Endpoint: GET /api/odontogramas/{paciente_id}/export-cda/
    
    Response: XML documento CDA descargable
    - Metadata del documento
    - Patient information
    - Odontograma section
    - Diagnósticos section
    - Plan de tratamiento section
    """
    
    try:
        paciente = Paciente.objects.get(id=paciente_id)
    except Paciente.DoesNotExist:
        return Response(
            {'error': 'Paciente no encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener odontólogo del request (usuario logueado)
    odontologo = request.user if request.user.is_authenticated else None
    
    # Generar CDA
    generator = CDAOdontogramGenerator(paciente, odontologo)
    cda_xml = generator.generar_cda()
    
    # Retornar como archivo XML descargable
    response = HttpResponse(cda_xml, content_type='application/xml')
    filename = f"odontograma_{paciente.id}_{paciente.nombres.replace(' ', '_')}.xml"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@api_view(['GET'])
def export_fhir_observation(request, diagnostico_id):
    """
    Exporta un diagnóstico individual como Observation FHIR.
    
    Endpoint: GET /api/diagnosticos/{diagnostico_id}/export-fhir/
    
    Response: JSON con un único recurso Observation/Condition/Procedure
    """
    
    from api.odontogram.models import DiagnosticoDental
    
    try:
        diagnostico = DiagnosticoDental.objects.get(id=diagnostico_id)
    except DiagnosticoDental.DoesNotExist:
        return Response(
            {'error': 'Diagnóstico no encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = ClinicalFindingFHIRSerializer(diagnostico)
    return Response(serializer.data, status=status.HTTP_200_OK)
