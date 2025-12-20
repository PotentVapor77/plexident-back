# patients/repositories/patient_repository.py
from ..models import Paciente
from django.core.exceptions import ObjectDoesNotExist

class PatientRepository:
    @staticmethod
    def get_all():
        return Paciente.objects.filter(activo=True).order_by('apellidos', 'nombres')  # ✅ CORREGIDO
    
    @staticmethod
    def get_by_id(id_paciente):
        try:
            return Paciente.objects.get(id=id_paciente, activo=True)
        except ObjectDoesNotExist:
            return None
    
    @staticmethod
    def create(**kwargs):
        paciente = Paciente(**kwargs)
        paciente.full_clean()
        paciente.save()
        return paciente
    
    @staticmethod
    def update(paciente, **kwargs):
        for key, value in kwargs.items():
            setattr(paciente, key, value)
        paciente.full_clean()
        paciente.save()
        return paciente
    
    @staticmethod
    def soft_delete(paciente):
        paciente.activo = False
        paciente.save()
