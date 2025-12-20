# patients/services/patient_service.py
from ..repositories.patient_repository import PatientRepository
from django.core.exceptions import ValidationError

class PatientService:
    @staticmethod
    def crear_paciente(data):
        try:
            return PatientRepository.create(**data)
        except ValidationError as e:
            raise ValidationError(f"Error de validación al crear paciente: {e}")
        except Exception as e:
            raise Exception(f"Error al crear paciente: {str(e)}")
    
    @staticmethod
    def listar_pacientes():
        try:
            return PatientRepository.get_all()
        except Exception as e:
            raise Exception(f"Error al listar pacientes: {str(e)}")
    
    @staticmethod
    def obtener_paciente(id_paciente):
        try:
            return PatientRepository.get_by_id(id_paciente)
        except Exception as e:
            raise Exception(f"Error al obtener paciente: {str(e)}")
    
    @staticmethod
    def actualizar_paciente(paciente, data):
        try:
            return PatientRepository.update(paciente, **data)
        except ValidationError as e:
            raise ValidationError(f"Error de validación al actualizar paciente: {e}")
        except Exception as e:
            raise Exception(f"Error al actualizar paciente: {str(e)}")
    
    @staticmethod
    def eliminar_paciente(paciente):
        try:
            PatientRepository.soft_delete(paciente)
        except Exception as e:
            raise Exception(f"Error al eliminar paciente: {str(e)}")