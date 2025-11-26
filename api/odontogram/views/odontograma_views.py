# api/odontogram/views/odontograma_views.py
"""
ViewSets para instancias de odontogramas
- Pacientes
- Dientes
- Superficies dentales
- Diagnósticos dentales aplicados
- Historial
"""

import logging
from django.shortcuts import get_object_or_404
from django.db.models import Q, Prefetch
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.odontogram.models import (
    Paciente,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma,
)

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

from api.odontogram.services.odontogram_services import OdontogramaService
from api.odontogram.serializers.bundle_serializers import FHIRBundleSerializer
from api.odontogram.serializers.serializers import DienteSerializer

logger = logging.getLogger(__name__)


class PacienteViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar pacientes"""
    
    permission_classes = [IsAuthenticated]
    
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
        """POST /api/diagnosticos-aplicados/{id}/marcar_tratado/"""
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
        return Response(
            {'error': 'No se pudo eliminar'},
            status=status.HTTP_400_BAD_REQUEST
        )


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