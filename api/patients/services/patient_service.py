from ..repositories.patient_repository import PatientRepository

class PatientService:
    @staticmethod
    def crear_paciente(data):
        return PatientRepository.create(**data)

    @staticmethod
    def listar_pacientes():
        return PatientRepository.get_all()

    @staticmethod
    def obtener_paciente(id_paciente):
        return PatientRepository.get_by_id(id_paciente)

    @staticmethod
    def actualizar_paciente(paciente, data):
        return PatientRepository.update(paciente, **data)

    @staticmethod
    def eliminar_paciente(paciente):
        PatientRepository.soft_delete(paciente)
