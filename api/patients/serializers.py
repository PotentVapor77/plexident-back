# api/patients/serializers.py

from rest_framework import serializers
from api.patients.models.paciente import Paciente
from api.patients.models.antecedentes_personales import AntecedentesPersonales
from api.patients.models.antecedentes_familiares import AntecedentesFamiliares
from api.patients.models.constantes_vitales import ConstantesVitales
from api.patients.models.examen_estomatognatico import ExamenEstomatognatico
from api.patients.models.anamnesis_general import AnamnesisGeneral


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
    """Serializer para antecedentes familiares de pacientes"""
    
    # Campos calculados de solo lectura
    paciente_nombre = serializers.CharField(source='paciente.get_full_name', read_only=True)
    paciente_cedula = serializers.CharField(source='paciente.cedula_pasaporte', read_only=True)
    
    class Meta:
        model = AntecedentesFamiliares
        fields = "__all__"
        read_only_fields = [
            "id", "creado_por", "actualizado_por", 
            "fecha_creacion", "fecha_modificacion",
            "paciente_nombre", "paciente_cedula"
        ]


    def to_representation(self, instance):
        """Personalizar representación para el frontend"""
        data = super().to_representation(instance)
        
        # Convertir fechas a ISO string
        if data.get('fecha_creacion'):
            data['fecha_creacion'] = instance.fecha_creacion.isoformat()
        if data.get('fecha_modificacion') and instance.fecha_modificacion:
            data['fecha_modificacion'] = instance.fecha_modificacion.isoformat()
        
        return data


    def validate_paciente(self, value):
        """Validar que el paciente exista y esté activo"""
        if not value.activo:
            raise serializers.ValidationError(
                "No se pueden crear antecedentes para un paciente inactivo"
            )
        
        return value


    def validate_cardiopatia_familiar(self, value):
        """Validar choices de cardiopatía"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value


    def validate_hipertension_arterial_familiar(self, value):
        """Validar choices de hipertensión"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value


    def validate_enfermedad_vascular_familiar(self, value):
        """Validar choices de enfermedad vascular"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value


    def validate_cancer_familiar(self, value):
        """Validar choices de cáncer"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value


    def validate_enfermedad_mental_familiar(self, value):
        """Validar choices de enfermedad mental"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value


    def validate_otros_antecedentes_familiares(self, value):
        """Validar longitud de otros antecedentes"""
        if value and len(value) > 500:
            raise serializers.ValidationError(
                "El campo 'otros antecedentes' no puede exceder 500 caracteres"
            )
        return value


    def validate(self, attrs):
        """Validaciones generales a nivel de objeto"""
        
        # Lista de campos con choices (no booleanos)
        campos_choices = [
            'cardiopatia_familiar',
            'hipertension_arterial_familiar',
            'enfermedad_vascular_familiar',
            'cancer_familiar',
            'enfermedad_mental_familiar'
        ]
        
        # Lista de campos booleanos
        campos_booleanos = [
            'endocrino_metabolico_familiar',
            'tuberculosis_familiar',
            'enfermedad_infecciosa_familiar',
            'malformacion_familiar'
        ]
        
        # Verificar que al menos un antecedente esté presente (solo en creación)
        if not self.instance:
            tiene_choice_activo = any(
                attrs.get(campo) and attrs.get(campo) != 'NO' 
                for campo in campos_choices
            )
            
            tiene_booleano_activo = any(
                attrs.get(campo) is True 
                for campo in campos_booleanos
            )
            
            tiene_otros = bool(attrs.get('otros_antecedentes_familiares', '').strip())
            
            if not (tiene_choice_activo or tiene_booleano_activo or tiene_otros):
                raise serializers.ValidationError(
                    "Debe proporcionar al menos un antecedente familiar"
                )
        
        # Validar coherencia: si hay "otros antecedentes", no puede estar vacío
        otros = attrs.get('otros_antecedentes_familiares', '').strip()
        if 'otros_antecedentes_familiares' in attrs and not otros:
            attrs['otros_antecedentes_familiares'] = ''
        
        return attrs

class ExamenEstomatognaticoSerializer(serializers.ModelSerializer):
    """Serializer para examen estomatognático"""
    
    # Campos calculados de solo lectura
    paciente_nombre = serializers.CharField(source='paciente.get_full_name', read_only=True)
    paciente_cedula = serializers.CharField(source='paciente.cedula_pasaporte', read_only=True)
    
    class Meta:
        model = ExamenEstomatognatico
        fields = "__all__"
        read_only_fields = [
            "id", "creado_por", "actualizado_por",
            "fecha_creacion", "fecha_modificacion",
            "paciente_nombre", "paciente_cedula",
            "tiene_patologias", "regiones_con_patologia", "atm_patologias"
        ]

    def to_representation(self, instance):
        """Personalizar representación para el frontend"""
        data = super().to_representation(instance)
        
        # Convertir fechas a ISO string
        if data.get('fecha_creacion'):
            data['fecha_creacion'] = instance.fecha_creacion.isoformat()
        if data.get('fecha_modificacion') and instance.fecha_modificacion:
            data['fecha_modificacion'] = instance.fecha_modificacion.isoformat()
        
        # Agregar propiedades calculadas
        data['tiene_patologias'] = instance.tiene_patologias
        data['regiones_con_patologia'] = instance.regiones_con_patologia
        data['atm_patologias'] = instance.atm_patologias
        data['total_regiones_anormales'] = len(instance.regiones_con_patologia)
        
        return data

    def validate_paciente(self, value):
        """Validar que el paciente exista y esté activo"""
        if not value.activo:
            raise serializers.ValidationError("No se pueden crear exámenes para un paciente inactivo")
        
        # 🚨 ELIMINADO: Validación de duplicados para permitir múltiples registros
        # if not self.instance:
        #     if ExamenEstomatognatico.objects.filter(paciente=value, activo=True).exists():
        #         raise serializers.ValidationError(
        #             "Ya existe un examen estomatognático activo para este paciente"
        #         )
        
        return value

    def validate(self, attrs):
        """Validaciones generales"""
        examen_sin_patologia = attrs.get('examen_sin_patologia', False)
        
        # Si está marcado "sin patología", todos los CP deben ser False
        if examen_sin_patologia:
            campos_cp = [
                'mejillas_cp', 'maxilar_inferior_cp', 'maxilar_superior_cp',
                'paladar_cp', 'piso_boca_cp', 'carrillos_cp',
                'glandulas_salivales_cp', 'ganglios_cp', 'lengua_cp',
                'labios_cp', 'atm_cp'
            ]
            
            for campo in campos_cp:
                if attrs.get(campo, False):
                    raise serializers.ValidationError(
                        f"No se puede marcar '{campo.replace('_cp', ' - Con Patología')}' "
                        f"si el examen está marcado como 'Sin Patología'"
                    )
        
        # Verificar coherencia CP/SP por región
        regiones = [
            ('mejillas', 'mejillas_cp', 'mejillas_sp'),
            ('maxilar_inferior', 'maxilar_inferior_cp', 'maxilar_inferior_sp'),
            ('maxilar_superior', 'maxilar_superior_cp', 'maxilar_superior_sp'),
            ('paladar', 'paladar_cp', 'paladar_sp'),
            ('piso_boca', 'piso_boca_cp', 'piso_boca_sp'),
            ('carrillos', 'carrillos_cp', 'carrillos_sp'),
            ('glandulas_salivales', 'glandulas_salivales_cp', 'glandulas_salivales_sp'),
            ('ganglios', 'ganglios_cp', 'ganglios_sp'),
            ('lengua', 'lengua_cp', 'lengua_sp'),
            ('labios', 'labios_cp', 'labios_sp'),
            ('atm', 'atm_cp', 'atm_sp'),
        ]
        
        for region_name, cp_field, sp_field in regiones:
            cp = attrs.get(cp_field, False)
            sp = attrs.get(sp_field, False)
            
            if cp and sp:
                raise serializers.ValidationError(
                    f"No se puede marcar tanto 'CP' como 'SP' para {region_name}"
                )
        
        return attrs



class ConstantesVitalesSerializer(serializers.ModelSerializer):
    """Serializer para constantes vitales"""
    
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    paciente_cedula = serializers.CharField(source='paciente.cedula_pasaporte', read_only=True)
    
    class Meta:
        model = ConstantesVitales
        fields = "__all__"
        read_only_fields = [
            "id", "creado_por", "actualizado_por",
            "fecha_creacion", "fecha_modificacion",
            "paciente_nombre", "paciente_cedula"
        ]
    
    def to_representation(self, instance):
        """Personalizar representación para el frontend"""
        data = super().to_representation(instance)
        
        # Convertir fechas a ISO string
        if data.get('fecha_consulta'):
            data['fecha_consulta'] = instance.fecha_consulta.isoformat()
        if data.get('fecha_creacion'):
            data['fecha_creacion'] = instance.fecha_creacion.isoformat()
        if data.get('fecha_modificacion') and instance.fecha_modificacion:
            data['fecha_modificacion'] = instance.fecha_modificacion.isoformat()
        
        return data

    def validate_temperatura(self, value):
        """Validar rango de temperatura corporal"""
        if value and (value < 35 or value > 42):
            raise serializers.ValidationError("La temperatura debe estar entre 35°C y 42°C")
        return value

    def validate_pulso(self, value):
        """Validar pulso"""
        if value and (value < 30 or value > 220):
            raise serializers.ValidationError("El pulso debe estar entre 30 y 220 lpm")
        return value

    def validate_frecuencia_respiratoria(self, value):
        """Validar frecuencia respiratoria"""
        if value and (value < 8 or value > 60):
            raise serializers.ValidationError("La frecuencia respiratoria debe estar entre 8 y 60 rpm")
        return value

    def validate_presion_arterial(self, value):
        """Validar formato de presión arterial"""
        if value:
            import re
            if not re.match(r'^\d{2,3}/\d{2,3}$', value):
                raise serializers.ValidationError("Formato inválido. Use formato: 120/80")
            
            # Validar que sistólica > diastólica
            sistolica, diastolica = map(int, value.split('/'))
            if sistolica <= diastolica:
                raise serializers.ValidationError("La presión sistólica debe ser mayor que la diastólica")
            if sistolica < 50 or sistolica > 250:
                raise serializers.ValidationError("La presión sistólica debe estar entre 50 y 250 mmHg")
            if diastolica < 30 or diastolica > 150:
                raise serializers.ValidationError("La presión diastólica debe estar entre 30 y 150 mmHg")
        
        return value

    def validate_paciente(self, value):
        """Validar que el paciente exista y esté activo"""
        if not value.activo:
            raise serializers.ValidationError("No se pueden crear constantes vitales para un paciente inactivo")
        
        return value
    

class AnamnesisGeneralSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    paciente_cedula = serializers.CharField(source='paciente.cedula_pasaporte', read_only=True)
    
    class Meta:
        model = AnamnesisGeneral
        fields = [
            'id',
            'paciente',
            'paciente_nombre',
            'paciente_cedula',
            
            # ========== ANTECEDENTES PERSONALES ==========
            'alergia_antibiotico',
            'alergia_antibiotico_otro',
            'alergia_anestesia',
            'alergia_anestesia_otro',
            'hemorragias',  # ✅ CAMBIADO
            'hemorragias_detalle',  # ✅ NUEVO
            
            'vih_sida',
            'vih_sida_otro',
            'tuberculosis',
            'tuberculosis_otro',
            'asma',
            'asma_otro',
            'diabetes',
            'diabetes_otro',
            'hipertension_arterial',  # ✅ CAMBIADO
            'hipertension_arterial_otro',  # ✅ CAMBIADO
            'enfermedad_cardiaca',
            'enfermedad_cardiaca_otro',  # ✅ CAMBIADO
            'otro_antecedente_personal',  # ✅ NUEVO
            
            # ========== ANTECEDENTES FAMILIARES ==========
            'cardiopatia_familiar',
            'cardiopatia_familiar_otro',
            'hipertension_familiar',
            'hipertension_familiar_otro',
            'enfermedad_cerebrovascular_familiar',  # ✅ NUEVO
            'enfermedad_cerebrovascular_familiar_otro',  # ✅ NUEVO
            'endocrino_metabolico_familiar',  # ✅ NUEVO
            'endocrino_metabolico_familiar_otro',  # ✅ NUEVO
            'cancer_familiar',
            'cancer_familiar_otro',
            'tuberculosis_familiar',  # ✅ NUEVO
            'tuberculosis_familiar_otro',  # ✅ NUEVO
            'enfermedad_mental_familiar',
            'enfermedad_mental_familiar_otro',
            'enfermedad_infecciosa_familiar',  # ✅ NUEVO
            'enfermedad_infecciosa_familiar_otro',  # ✅ NUEVO
            'malformacion_familiar',  # ✅ NUEVO
            'malformacion_familiar_otro',  # ✅ NUEVO
            'otro_antecedente_familiar',  # ✅ NUEVO
            
            # ========== HÁBITOS Y OBSERVACIONES ==========
            'habitos',
            'observaciones',
            
            # ========== METADATA ==========
            'activo',
            'fecha_creacion',
            'fecha_modificacion',
            'creado_por',
            'actualizado_por',
        ]
        read_only_fields = [
            'id', 
            'fecha_creacion', 
            'fecha_modificacion', 
            'creado_por', 
            'actualizado_por',
            'paciente_nombre',
            'paciente_cedula'
        ]
    
    def to_representation(self, instance):
        """Personalizar representación para el frontend"""
        data = super().to_representation(instance)
        
        # Convertir fechas a ISO string
        if data.get('fecha_creacion'):
            data['fecha_creacion'] = instance.fecha_creacion.isoformat()
        if data.get('fecha_modificacion') and instance.fecha_modificacion:
            data['fecha_modificacion'] = instance.fecha_modificacion.isoformat()
        
        # Agregar propiedades del modelo
        data['tiene_condiciones_importantes'] = instance.tiene_condiciones_importantes
        data['resumen_condiciones'] = instance.resumen_condiciones
        
        return data
    
    def validate(self, data):
        """Validaciones personalizadas basadas en el modelo"""
        # Validar campos "Otro" que requieren especificación
        campos_otro_validacion = [
            ('alergia_antibiotico', 'alergia_antibiotico_otro', 'OTRO'),
            ('alergia_anestesia', 'alergia_anestesia_otro', 'OTRO'),
            ('vih_sida', 'vih_sida_otro', 'OTRO'),
            ('tuberculosis', 'tuberculosis_otro', 'OTRO'),
            ('asma', 'asma_otro', 'OTRO'),
            ('diabetes', 'diabetes_otro', 'OTRO'),
            ('hipertension_arterial', 'hipertension_arterial_otro', 'OTRO'),  # ✅ CAMBIADO
            ('enfermedad_cardiaca', 'enfermedad_cardiaca_otro', 'OTRO'),  # ✅ CAMBIADO
            ('cardiopatia_familiar', 'cardiopatia_familiar_otro', 'OTRO'),
            ('hipertension_familiar', 'hipertension_familiar_otro', 'OTRO'),
            ('enfermedad_cerebrovascular_familiar', 'enfermedad_cerebrovascular_familiar_otro', 'OTRO'),
            ('endocrino_metabolico_familiar', 'endocrino_metabolico_familiar_otro', 'OTRO'),
            ('cancer_familiar', 'cancer_familiar_otro', 'OTRO'),
            ('tuberculosis_familiar', 'tuberculosis_familiar_otro', 'OTRO'),
            ('enfermedad_mental_familiar', 'enfermedad_mental_familiar_otro', 'OTRO'),
            ('enfermedad_infecciosa_familiar', 'enfermedad_infecciosa_familiar_otro', 'OTRO'),
            ('malformacion_familiar', 'malformacion_familiar_otro', 'OTRO'),
        ]
        
        for campo_select, campo_otro, valor_otro in campos_otro_validacion:
            valor_select = data.get(campo_select)
            valor_otro_field = data.get(campo_otro)
            
            # Si estamos actualizando y el campo no está en data, usar el valor actual
            if self.instance and valor_select is None:
                valor_select = getattr(self.instance, campo_select)
            if self.instance and valor_otro_field is None:
                valor_otro_field = getattr(self.instance, campo_otro)
            
            if valor_select == valor_otro and not valor_otro_field:
                # Obtener nombre display del campo
                field = self.Meta.model._meta.get_field(campo_select)
                nombre_display = dict(field.choices).get(valor_select, valor_select)
                raise serializers.ValidationError({
                    campo_otro: f'Debe especificar cuando selecciona "{nombre_display}"'
                })
        
        return data
    
    def create(self, validated_data):
        """Crear anamnesis general"""
        validated_data['creado_por'] = self.context['request'].user
        validated_data['actualizado_por'] = self.context['request'].user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Actualizar anamnesis general"""
        validated_data['actualizado_por'] = self.context['request'].user
        return super().update(instance, validated_data)