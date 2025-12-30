# api/patients/serializers.py

from rest_framework import serializers
from api.patients.models.paciente import Paciente
from api.patients.models.antecedentes_personales import AntecedentesPersonales
from api.patients.models.antecedentes_familiares import AntecedentesFamiliares
from api.patients.models.constantes_vitales import ConstantesVitales
from api.patients.models.examen_estomatognatico import ExamenEstomatognatico


class PacienteSerializer(serializers.ModelSerializer):
    """Serializer para lectura y escritura de pacientes"""
    
    class Meta:
        model = Paciente
        fields = '__all__'
        read_only_fields = [
            'id', 'creado_por', 'actualizado_por',
            'fecha_creacion', 'fecha_modificacion'
        ]

    def to_representation(self, instance):
        """Formato compatible con frontend"""
        data = super().to_representation(instance)
        
        # Convertir fechas a ISO string
        if data.get('fecha_nacimiento'):
            data['fecha_nacimiento'] = instance.fecha_nacimiento.isoformat()
        if data.get('fecha_creacion'):
            data['fecha_creacion'] = instance.fecha_creacion.isoformat()
        if data.get('fecha_modificacion') and instance.fecha_modificacion:
            data['fecha_modificacion'] = instance.fecha_modificacion.isoformat()
        
        return data

    def validate_nombres(self, value):
        """Validar que los nombres no estén vacíos"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Los nombres son obligatorios")
        return value.strip()

    def validate_apellidos(self, value):
        """Validar que los apellidos no estén vacíos"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Los apellidos son obligatorios")
        return value.strip()

    def validate_cedula_pasaporte(self, value):
        """Validar cédula/pasaporte único"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("La cédula/pasaporte es obligatoria")
        
        # Verificar duplicados (excepto el mismo paciente en caso de update)
        instance = getattr(self, 'instance', None)
        if instance:
            if Paciente.objects.filter(cedula_pasaporte=value).exclude(pk=instance.pk).exists():
                raise serializers.ValidationError("Esta cédula/pasaporte ya está registrada")
        else:
            if Paciente.objects.filter(cedula_pasaporte=value).exists():
                raise serializers.ValidationError("Esta cédula/pasaporte ya está registrada")
        
        return value.strip()

    def validate_telefono(self, value):
        """Validar formato de teléfono"""
        if value and (len(value) < 10 or not value.isdigit()):
            raise serializers.ValidationError("El teléfono debe tener al menos 10 números")
        return value

    def validate_contacto_emergencia_telefono(self, value):
        """Validar teléfono de emergencia"""
        if value and (len(value) < 10 or not value.isdigit()):
            raise serializers.ValidationError("El teléfono de emergencia debe tener al menos 10 números")
        return value

    def validate_edad(self, value):
        """Validar rango de edad"""
        if value is not None and (value <= 0 or value > 150):
            raise serializers.ValidationError("La edad debe estar entre 1 y 150 años")
        return value

    def validate_correo(self, value):
        """Validar formato de correo electrónico"""
        if value:
            import re
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, value):
                raise serializers.ValidationError("El correo electrónico no es válido")
        return value

    def validate(self, attrs):
        """Validaciones generales a nivel de objeto"""
        # Validar que un paciente masculino no esté marcado como embarazado
        if attrs.get('sexo') == 'M' and attrs.get('embarazada') == 'SI':
            raise serializers.ValidationError(
                {"embarazada": "Un paciente masculino no puede estar marcado como embarazado"}
            )
        
        # Validar campos obligatorios
        if not attrs.get('nombres'):
            raise serializers.ValidationError({"nombres": "Los nombres son obligatorios"})
        if not attrs.get('apellidos'):
            raise serializers.ValidationError({"apellidos": "Los apellidos son obligatorios"})
        if not attrs.get('cedula_pasaporte'):
            raise serializers.ValidationError({"cedula_pasaporte": "La cédula/pasaporte es obligatoria"})
        
        return attrs


class ConstantesVitalesSerializer(serializers.ModelSerializer):
    """Serializer para constantes vitales"""
    
    class Meta:
        model = ConstantesVitales
        fields = "__all__"
        read_only_fields = [
            "id", "creado_por", "actualizado_por",
            "fecha_creacion", "fecha_modificacion",
        ]

    def validate_temperatura(self, value):
        """Validar rango de temperatura corporal"""
        if value and (value < 35 or value > 42):
            raise serializers.ValidationError("La temperatura debe estar entre 35°C y 42°C")
        return value

    def validate_presion_arterial_sistolica(self, value):
        """Validar presión sistólica"""
        if value and (value < 50 or value > 250):
            raise serializers.ValidationError("La presión sistólica debe estar entre 50 y 250 mmHg")
        return value

    def validate_presion_arterial_diastolica(self, value):
        """Validar presión diastólica"""
        if value and (value < 30 or value > 150):
            raise serializers.ValidationError("La presión diastólica debe estar entre 30 y 150 mmHg")
        return value

    def validate_frecuencia_cardiaca(self, value):
        """Validar frecuencia cardíaca"""
        if value and (value < 30 or value > 220):
            raise serializers.ValidationError("La frecuencia cardíaca debe estar entre 30 y 220 lpm")
        return value

    def validate_frecuencia_respiratoria(self, value):
        """Validar frecuencia respiratoria"""
        if value and (value < 8 or value > 60):
            raise serializers.ValidationError("La frecuencia respiratoria debe estar entre 8 y 60 rpm")
        return value

    def validate(self, attrs):
        """Validación de presión arterial completa"""
        sistolica = attrs.get('presion_arterial_sistolica')
        diastolica = attrs.get('presion_arterial_diastolica')
        
        # Si ambas están presentes, validar que sistólica > diastólica
        if sistolica and diastolica:
            if sistolica <= diastolica:
                raise serializers.ValidationError(
                    "La presión sistólica debe ser mayor que la diastólica"
                )
        
        return attrs


class AntecedentesPersonalesSerializer(serializers.ModelSerializer):
    """Serializer para antecedentes personales de pacientes"""
    
    paciente_nombre = serializers.CharField(source='paciente.get_full_name', read_only=True)
    paciente_cedula = serializers.CharField(source='paciente.cedula_pasaporte', read_only=True)
    
    class Meta:
        model = AntecedentesPersonales
        fields = "__all__"
        read_only_fields = [
            "id", "creado_por", "actualizado_por", 
            "fecha_creacion", "fecha_modificacion",
            "paciente_nombre", "paciente_cedula"
        ]

    def validate_paciente(self, value):
        """Validar que el paciente exista y esté activo"""
        if not value.activo:
            raise serializers.ValidationError("No se pueden crear antecedentes para un paciente inactivo")
        return value

    def validate(self, attrs):
        """Validaciones generales"""
        # Validar que al menos un campo de antecedentes tenga información
        campos_antecedentes = [
            'enfermedades_corazon', 'enfermedades_pulmonares', 'diabetes',
            'hipertension', 'hepatitis', 'vih_sida', 'alergias',
            'medicamentos_actuales', 'cirugias_previas', 'hospitalizaciones'
        ]
        
        # Verificar si al menos un campo tiene contenido
        tiene_datos = any(attrs.get(campo) for campo in campos_antecedentes)
        
        if not tiene_datos and self.instance is None:  # Solo en creación
            raise serializers.ValidationError(
                "Debe proporcionar al menos un antecedente personal"
            )
        
        return attrs


class AntecedentesFamiliaresSerializer(serializers.ModelSerializer):
    """Serializer para antecedentes familiares"""
    
    paciente_nombre = serializers.CharField(source='paciente.get_full_name', read_only=True)
    
    class Meta:
        model = AntecedentesFamiliares
        fields = "__all__"
        read_only_fields = [
            "id", "creado_por", "actualizado_por", 
            "fecha_creacion", "fecha_modificacion",
            "paciente_nombre"
        ]

    def validate_paciente(self, value):
        """Validar que el paciente exista y esté activo"""
        if not value.activo:
            raise serializers.ValidationError("No se pueden crear antecedentes para un paciente inactivo")
        return value


class ExamenEstomatognaticoSerializer(serializers.ModelSerializer):
    """Serializer para examen estomatognático"""
    
    paciente_nombre = serializers.CharField(source='paciente.get_full_name', read_only=True)
    
    class Meta:
        model = ExamenEstomatognatico
        fields = "__all__"
        read_only_fields = [
            "id", "creado_por", "actualizado_por", 
            "fecha_creacion", "fecha_modificacion",
            "paciente_nombre"
        ]

    def validate_paciente(self, value):
        """Validar que el paciente exista y esté activo"""
        if not value.activo:
            raise serializers.ValidationError("No se pueden crear exámenes para un paciente inactivo")
        return value
