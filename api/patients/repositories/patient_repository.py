from ..models import Paciente

class PatientRepository:
    @staticmethod
    def get_all():
        return Paciente.objects.filter(status=True)

    @staticmethod
    def get_by_id(id_paciente):
        return Paciente.objects.filter(id_paciente=id_paciente, status=True).first()

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
        paciente.status = False
        paciente.save()
