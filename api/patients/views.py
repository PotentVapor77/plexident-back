# api/patients/views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination

from api.patients.models.paciente import Paciente
from api.patients.serializers import PacienteSerializer
from api.patients.services.patient_service import PatientService


class PacientePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PacienteViewSet(viewsets.ModelViewSet):
    serializer_class = PacienteSerializer
    queryset = Paciente.objects.all()  # Sin filtro activo aquí, se maneja en métodos
    pagination_class = PacientePagination
    # permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['sexo', 'activo', 'condicion_edad']
    search_fields = [
        'nombres', 'apellidos',
        'cedula_pasaporte', 'telefono', 'correo',
    ]
    ordering_fields = ['apellidos', 'nombres', 'fecha_creacion', 'edad']
    ordering = ['apellidos', 'nombres']

    def get_queryset(self):
        """Solo pacientes activos por defecto"""
        return Paciente.objects.filter(activo=True)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'next': None,
            'previous': None,
            'results': serializer.data
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        paciente = PatientService.crear_paciente(serializer.validated_data)
        output_serializer = self.get_serializer(paciente)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        paciente = PatientService.actualizar_paciente(instance, serializer.validated_data)
        output_serializer = self.get_serializer(paciente)
        return Response(output_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        PatientService.eliminar_paciente(instance)
        return Response({'id': str(instance.id)})

    @action(detail=True, methods=['patch'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        instance = self.get_object()
        instance.activo = not instance.activo
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
