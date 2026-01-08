import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

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
    """ViewSet para gestionar Planes de Tratamiento"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = PlanTratamiento.objects.filter(activo=True)
        paciente_id = self.request.query_params.get('paciente_id')
        
        if paciente_id:
            queryset = queryset.filter(paciente_id=paciente_id)
        
        return queryset.select_related('paciente', 'creado_por').prefetch_related('sesiones')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PlanTratamientoDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PlanTratamientoCreateSerializer
        return PlanTratamientoListSerializer
    
    def perform_create(self, serializer):
        service = PlanTratamientoService()
        paciente_id = serializer.validated_data['paciente'].id
        
        plan = service.crear_plan_tratamiento(
            paciente_id=str(paciente_id),
            odontologo_id=self.request.user.id,
            titulo=serializer.validated_data.get('titulo', 'Plan de Tratamiento'),
            notas_generales=serializer.validated_data.get('notas_generales', ''),
            usar_ultimo_odontograma=serializer.validated_data.get('usar_ultimo_odontograma', True)
        )
        
        return plan
    
    @action(detail=True, methods=['get'])
    def diagnosticos_disponibles(self, request, pk=None):
        """
        GET /api/planes-tratamiento/{id}/diagnosticos-disponibles/
        Retorna diagnósticos del último odontograma para autocompletar
        """
        plan = self.get_object()
        service = PlanTratamientoService()
        
        diagnosticos_data = service.obtener_diagnosticos_ultimo_odontograma(
            str(plan.paciente.id)
        )
        
        return Response(diagnosticos_data, status=status.HTTP_200_OK)


class SesionTratamientoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar Sesiones de Tratamiento"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = SesionTratamiento.objects.filter(activo=True)
        
        plan_id = self.request.query_params.get('plan_id')
        paciente_id = self.request.query_params.get('paciente_id')
        estado = self.request.query_params.get('estado')
        
        if plan_id:
            queryset = queryset.filter(plan_tratamiento_id=plan_id)
        
        if paciente_id:
            queryset = queryset.filter(plan_tratamiento__paciente_id=paciente_id)
        
        if estado:
            queryset = queryset.filter(estado=estado)
        
        return queryset.select_related(
            'plan_tratamiento', 
            'plan_tratamiento__paciente', 
            'odontologo'
        ).order_by('plan_tratamiento', 'numero_sesion')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SesionTratamientoDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SesionTratamientoCreateSerializer
        return SesionTratamientoListSerializer
    
    def perform_create(self, serializer):
        service = PlanTratamientoService()
        
        sesion = service.crear_sesion_tratamiento(
            plan_tratamiento_id=str(serializer.validated_data['plan_tratamiento'].id),
            odontologo_id=self.request.user.id,
            fecha_programada=serializer.validated_data.get('fecha_programada'),
            autocompletar_diagnosticos=serializer.validated_data.get('autocompletar_diagnosticos', True),
            procedimientos=serializer.validated_data.get('procedimientos', []),
            prescripciones=serializer.validated_data.get('prescripciones', []),
            notas=serializer.validated_data.get('notas', '')
        )
        
        return sesion
    
    @action(detail=True, methods=['post'])
    def firmar(self, request, pk=None):
        """
        POST /api/sesiones-tratamiento/{id}/firmar/
        Body: { "firma_digital": "base64_string_or_hash" }
        """
        sesion = self.get_object()
        service = PlanTratamientoService()
        
        firma_digital = request.data.get('firma_digital')
        
        sesion = service.firmar_sesion(
            sesion_id=str(sesion.id),
            odontologo_id=request.user.id,
            firma_digital=firma_digital
        )
        
        serializer = SesionTratamientoDetailSerializer(sesion)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def completar(self, request, pk=None):
        """
        POST /api/sesiones-tratamiento/{id}/completar/
        Marca la sesión como completada
        """
        sesion = self.get_object()
        
        from django.utils import timezone
        sesion.estado = SesionTratamiento.EstadoSesion.COMPLETADA
        sesion.fecha_realizacion = timezone.now()
        sesion.save()
        
        serializer = SesionTratamientoDetailSerializer(sesion)
        return Response(serializer.data, status=status.HTTP_200_OK)
