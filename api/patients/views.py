from rest_framework import viewsets, permissions
from .models import Paciente
from .serializers import PacienteSerializer
from .services.patient_service import PatientService

class PacienteViewSet(viewsets.ModelViewSet):
    serializer_class = PacienteSerializer
    queryset = Paciente.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        data = serializer.validated_data
        PatientService.crear_paciente(data)

    def perform_update(self, serializer):
        paciente = self.get_object()
        PatientService.actualizar_paciente(paciente, serializer.validated_data)

    def perform_destroy(self, instance):
        PatientService.eliminar_paciente(instance)
