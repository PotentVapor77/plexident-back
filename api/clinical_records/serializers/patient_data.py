# src/api/clinical_records/serializers/patient_data.py
"""
Serializers para datos de paciente y establecimiento
"""
from rest_framework import serializers


class PatientInfoMixin:
    """Mixin para información expandida del paciente"""
    
    def get_paciente_info(self, obj):
        """Información del paciente"""
        if not obj.paciente:
            return None
        return {
            'id': str(obj.paciente.id),
            'nombres': obj.paciente.nombres,
            'apellidos': obj.paciente.apellidos,
            'cedula_pasaporte': obj.paciente.cedula_pasaporte,
            'sexo': obj.paciente.sexo,
            'edad': obj.paciente.edad,
            'fecha_nacimiento': (
                obj.paciente.fecha_nacimiento.isoformat()
                if obj.paciente.fecha_nacimiento
                else None
            ),
        }
    
    def get_odontologo_info(self, obj):
        """Información del odontólogo responsable"""
        if not obj.odontologo_responsable:
            return None
        return {
            'id': str(obj.odontologo_responsable.id),
            'nombres': obj.odontologo_responsable.nombres,
            'apellidos': obj.odontologo_responsable.apellidos,
            'rol': obj.odontologo_responsable.rol,
        }
    
    def get_creado_por_info(self, obj):
        """Información del usuario que creó el historial"""
        if not obj.creado_por:
            return None
        return {
            'id': str(obj.creado_por.id),
            'nombres': obj.creado_por.nombres,
            'apellidos': obj.creado_por.apellidos,
        }
