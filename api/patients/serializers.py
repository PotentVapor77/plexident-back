# api/patients/serializers.py

from rest_framework import serializers
from api.patients.models.paciente import Paciente
from api.patients.models.antecedentes_personales import AntecedentesPersonales
from api.patients.models.antecedentes_familiares import AntecedentesFamiliares
from api.patients.models.constantes_vitales import ConstantesVitales
from api.patients.models.examen_estomatognatico import ExamenEstomatognatico
from api.patients.models.examenes_complementarios import ExamenesComplementarios


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
    fecha_consulta = serializers.DateField(format='%Y-%m-%d')
    fecha_creacion = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S', read_only=True)
    fecha_modificacion = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S', read_only=True)
    
    class Meta:
        model = ConstantesVitales
        fields = '__all__'
        read_only_fields = ('fecha_creacion', 'fecha_modificacion', 'creado_por', 'actualizado_por')
    
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
    


class AntecedentesPersonalesSerializer(serializers.ModelSerializer):
    """Serializer para antecedentes personales de pacientes"""
    
    # Campos calculados de solo lectura (opcionales)
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    paciente_cedula = serializers.CharField(source='paciente.cedula_pasaporte', read_only=True)
    
    class Meta:
        model = AntecedentesPersonales
        fields = "__all__"
        read_only_fields = [
            "id", "creado_por", "actualizado_por", 
            "fecha_creacion", "fecha_modificacion",
            "paciente_nombre", "paciente_cedula"  # ← Solo estos
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
    
    def validate_alergia_antibiotico(self, value):
        """Validar choices de alergia antibiótico"""
        valid_choices = ['NO', 'PENICILINA', 'SULFA', 'CEFALOSPORINAS', 'MACROLIDOS', 'OTRO']  # ✅ Actualizado
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_alergia_anestesia(self, value):
        """Validar choices de alergia anestesia"""
        valid_choices = ['NO', 'LOCAL', 'GENERAL', 'AMBAS', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_hemorragias(self, value):
        """Validar choices de hemorragias"""
        valid_choices = ['NO', 'SI']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_vih_sida(self, value):
        """Validar choices de VIH/SIDA"""
        valid_choices = ['NEGATIVO', 'POSITIVO', 'DESCONOCIDO', 'OTRO']  # ✅ Agregado 'OTRO'
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_tuberculosis(self, value):
        """Validar choices de tuberculosis"""
        valid_choices = ['NUNCA', 'TRATADA', 'ACTIVA', 'DESCONOCIDO', 'OTRO']  # ✅ Agregado 'OTRO'
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_asma(self, value):
        """Validar choices de asma"""
        valid_choices = ['NO', 'LEVE', 'MODERADA', 'SEVERA', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_diabetes(self, value):
        """Validar choices de diabetes"""
        valid_choices = ['NO', 'PREDIABETICO', 'TIPO_1', 'TIPO_2', 'GESTACIONAL', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_hipertension_arterial(self, value):
        """Validar choices de hipertensión"""
        valid_choices = ['NO', 'CONTROLADA', 'NO_CONTROLADA', 'SIN_TRATAMIENTO', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_enfermedad_cardiaca(self, value):
        """Validar choices de enfermedad cardíaca"""
        valid_choices = ['NO', 'ARRITMIA', 'INSUFICIENCIA', 'CONGENITA', 'OTRO']  # ✅ Cambiado 'OTRA' a 'OTRO'
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate(self, attrs):
        """Validaciones generales"""
        
        # Lista de TODOS los campos con sus correspondientes _otro
        campos_validar = [
            ('alergia_antibiotico', 'alergia_antibiotico_otro', 'OTRO'),
            ('alergia_anestesia', 'alergia_anestesia_otro', 'OTRO'),
            ('vih_sida', 'vih_sida_otro', 'OTRO'),  # ✅ Agregado
            ('tuberculosis', 'tuberculosis_otro', 'OTRO'),  # ✅ Agregado
            ('asma', 'asma_otro', 'OTRO'),
            ('diabetes', 'diabetes_otro', 'OTRO'),
            ('hipertension_arterial', 'hipertension_arterial_otro', 'OTRO'),
            ('enfermedad_cardiaca', 'enfermedad_cardiaca_otro', 'OTRO'),  # ✅ Cambiado 'OTRA' a 'OTRO'
        ]
        
        # Validación para todos los campos con _otro
        for campo_principal, campo_otro, valor_otro in campos_validar:
            valor_principal = attrs.get(campo_principal)
            valor_otro_text = attrs.get(campo_otro, '')
            
            # 1. Si NO es OTRO, el campo _otro debe estar vacío
            if valor_principal and valor_principal != valor_otro and valor_otro_text:
                campo_nombre = campo_principal.replace('_', ' ').title()
                raise serializers.ValidationError({
                    campo_otro: f'No debe especificar detalles cuando selecciona "{valor_principal}". '
                               f'Solo complete este campo si selecciona "{valor_otro}".'
                })
            
            # 2. Si es OTRO, el campo _otro es requerido
            if valor_principal == valor_otro and not valor_otro_text:
                tipo_error = campo_principal.replace('_', ' ')
                raise serializers.ValidationError({
                    campo_otro: f'Debe especificar el tipo de {tipo_error} cuando selecciona "{valor_otro}"'
                })
        
        # Validación específica para hemorragias
        if attrs.get('hemorragias') != 'SI' and attrs.get('hemorragias_detalle'):
            raise serializers.ValidationError({
                'hemorragias_detalle': 'Solo debe especificar detalles de hemorragias si selecciona "SI"'
            })
        
        if attrs.get('hemorragias') == 'SI' and not attrs.get('hemorragias_detalle'):
            raise serializers.ValidationError({
                'hemorragias_detalle': 'Debe especificar detalles de hemorragias'
            })
        
        # ✅ CORRECCIÓN: Actualizar validación para diabetes_otro
        # Ahora diabetes_otro solo se usa cuando diabetes es "OTRO"
        if attrs.get('diabetes') != 'OTRO' and attrs.get('diabetes_otro'):
            raise serializers.ValidationError({
                'diabetes_otro': 'Solo debe especificar detalles de diabetes cuando selecciona "OTRO"'
            })
        
        # Validación de longitud de campos de texto
        if attrs.get('otros_antecedentes_personales') and len(attrs['otros_antecedentes_personales']) > 1000:
            raise serializers.ValidationError({
                'otros_antecedentes_personales': 'El campo no puede exceder 1000 caracteres'
            })
        
        if attrs.get('habitos') and len(attrs['habitos']) > 1000:
            raise serializers.ValidationError({
                'habitos': 'El campo no puede exceder 1000 caracteres'
            })
        
        if attrs.get('observaciones') and len(attrs['observaciones']) > 1000:
            raise serializers.ValidationError({
                'observaciones': 'El campo no puede exceder 1000 caracteres'
            })
        
        # Validación adicional: hemorragias_detalle no debe exceder 500 caracteres
        if attrs.get('hemorragias_detalle') and len(attrs['hemorragias_detalle']) > 500:
            raise serializers.ValidationError({
                'hemorragias_detalle': 'El campo no puede exceder 500 caracteres'
            })
        
        # Validación adicional: campos _otro no deben exceder 100 caracteres
        campos_otro = [
            'alergia_antibiotico_otro', 'alergia_anestesia_otro', 'vih_sida_otro',
            'tuberculosis_otro', 'asma_otro', 'diabetes_otro',
            'hipertension_arterial_otro', 'enfermedad_cardiaca_otro'
        ]
        
        for campo in campos_otro:
            if attrs.get(campo) and len(attrs[campo]) > 100:
                raise serializers.ValidationError({
                    campo: 'El campo no puede exceder 100 caracteres'
                })
        
        return attrs


class AntecedentesFamiliaresSerializer(serializers.ModelSerializer):
    """Serializer para antecedentes familiares de pacientes"""
    
    # Campos calculados de solo lectura (opcionales)
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    paciente_cedula = serializers.CharField(source='paciente.cedula_pasaporte', read_only=True)
    
    class Meta:
        model = AntecedentesFamiliares
        fields = "__all__"
        read_only_fields = [
            "id", "creado_por", "actualizado_por", 
            "fecha_creacion", "fecha_modificacion",
            "paciente_nombre", "paciente_cedula"  # ← Solo estos
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
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_hipertension_arterial_familiar(self, value):
        """Validar choices de hipertensión"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_enfermedad_vascular_familiar(self, value):
        """Validar choices de enfermedad vascular"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_endocrino_metabolico_familiar(self, value):
        """Validar choices de endócrino metabólico"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_cancer_familiar(self, value):
        """Validar choices de cáncer"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_tuberculosis_familiar(self, value):
        """Validar choices de tuberculosis"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_enfermedad_mental_familiar(self, value):
        """Validar choices de enfermedad mental"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_enfermedad_infecciosa_familiar(self, value):
        """Validar choices de enfermedad infecciosa"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_malformacion_familiar(self, value):
        """Validar choices de malformación"""
        valid_choices = ['NO', 'PADRE', 'MADRE', 'HERMANOS', 'ABUELOS', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_tipo_cancer(self, value):
        """Validar choices de tipo de cáncer"""
        valid_choices = ['MAMA', 'PULMON', 'PROSTATA', 'COLORRECTAL', 'CERVICOUTERINO', 'OTRO']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_otros_antecedentes_familiares(self, value):
        """Validar longitud de otros antecedentes"""
        if value and len(value) > 1000:
            raise serializers.ValidationError(
                "El campo 'otros antecedentes' no puede exceder 1000 caracteres"
            )
        return value
    
    def validate(self, attrs):
        """Validaciones generales a nivel de objeto"""
        
        # Lista de campos para validación
        campos_validar = [
            ('cardiopatia_familiar', 'cardiopatia_familiar_otro'),
            ('hipertension_arterial_familiar', 'hipertension_arterial_familiar_otro'),
            ('enfermedad_vascular_familiar', 'enfermedad_vascular_familiar_otro'),
            ('endocrino_metabolico_familiar', 'endocrino_metabolico_familiar_otro'),
            ('cancer_familiar', 'cancer_familiar_otro'),
            ('tuberculosis_familiar', 'tuberculosis_familiar_otro'),
            ('enfermedad_mental_familiar', 'enfermedad_mental_familiar_otro'),
            ('enfermedad_infecciosa_familiar', 'enfermedad_infecciosa_familiar_otro'),
            ('malformacion_familiar', 'malformacion_familiar_otro'),
        ]
        
        # Validación 1: Campos _otro solo cuando principal es "OTRO"
        for campo_principal, campo_otro in campos_validar:
            valor_principal = attrs.get(campo_principal)
            valor_otro = attrs.get(campo_otro, '')
            
            if valor_principal and valor_principal != 'OTRO' and valor_otro:
                raise serializers.ValidationError({
                    campo_otro: f'No debe especificar familiar "otro" cuando selecciona "{valor_principal}". '
                               f'Solo complete este campo si selecciona "OTRO" como familiar.'
                })
        
        # Validación 2: Campos _otro requeridos cuando principal es "OTRO"
        for campo_principal, campo_otro in campos_validar:
            valor_principal = attrs.get(campo_principal)
            valor_otro = attrs.get(campo_otro, '')
            
            if valor_principal == 'OTRO' and not valor_otro:
                raise serializers.ValidationError({
                    campo_otro: f'Debe especificar el familiar cuando selecciona "OTRO"'
                })
        
        # Validación 3: Campos "OTRO" que requieren especificación
        if attrs.get('cardiopatia_familiar') == 'OTRO' and not attrs.get('cardiopatia_familiar_otro'):
            raise serializers.ValidationError({
                'cardiopatia_familiar_otro': 'Debe especificar el familiar cuando selecciona "Otro"'
            })
        
        if attrs.get('hipertension_arterial_familiar') == 'OTRO' and not attrs.get('hipertension_arterial_familiar_otro'):
            raise serializers.ValidationError({
                'hipertension_arterial_familiar_otro': 'Debe especificar el familiar cuando selecciona "Otro"'
            })
        
        if attrs.get('enfermedad_vascular_familiar') == 'OTRO' and not attrs.get('enfermedad_vascular_familiar_otro'):
            raise serializers.ValidationError({
                'enfermedad_vascular_familiar_otro': 'Debe especificar el familiar cuando selecciona "Otro"'
            })
        
        if attrs.get('endocrino_metabolico_familiar') == 'OTRO' and not attrs.get('endocrino_metabolico_familiar_otro'):
            raise serializers.ValidationError({
                'endocrino_metabolico_familiar_otro': 'Debe especificar el familiar cuando selecciona "Otro"'
            })
        
        if attrs.get('cancer_familiar') == 'OTRO' and not attrs.get('cancer_familiar_otro'):
            raise serializers.ValidationError({
                'cancer_familiar_otro': 'Debe especificar el familiar cuando selecciona "Otro"'
            })
        
        if attrs.get('tuberculosis_familiar') == 'OTRO' and not attrs.get('tuberculosis_familiar_otro'):
            raise serializers.ValidationError({
                'tuberculosis_familiar_otro': 'Debe especificar el familiar cuando selecciona "Otro"'
            })
        
        if attrs.get('enfermedad_mental_familiar') == 'OTRO' and not attrs.get('enfermedad_mental_familiar_otro'):
            raise serializers.ValidationError({
                'enfermedad_mental_familiar_otro': 'Debe especificar el familiar cuando selecciona "Otro"'
            })
        
        if attrs.get('enfermedad_infecciosa_familiar') == 'OTRO' and not attrs.get('enfermedad_infecciosa_familiar_otro'):
            raise serializers.ValidationError({
                'enfermedad_infecciosa_familiar_otro': 'Debe especificar el familiar cuando selecciona "Otro"'
            })
        
        if attrs.get('malformacion_familiar') == 'OTRO' and not attrs.get('malformacion_familiar_otro'):
            raise serializers.ValidationError({
                'malformacion_familiar_otro': 'Debe especificar el familiar cuando selecciona "Otro"'
            })
        
        # Validar tipo de cáncer
        if attrs.get('cancer_familiar') and attrs.get('cancer_familiar') != 'NO':
            if not attrs.get('tipo_cancer'):
                raise serializers.ValidationError({
                    'tipo_cancer': 'Debe especificar el tipo de cáncer'
                })
        
        if attrs.get('tipo_cancer') == 'OTRO' and not attrs.get('tipo_cancer_otro'):
            raise serializers.ValidationError({
                'tipo_cancer_otro': 'Debe especificar el tipo de cáncer cuando selecciona "Otro"'
            })
        
        # Validar que tipo_cancer_otro esté vacío si no es OTRO
        if attrs.get('tipo_cancer') and attrs.get('tipo_cancer') != 'OTRO' and attrs.get('tipo_cancer_otro'):
            raise serializers.ValidationError({
                'tipo_cancer_otro': 'Solo debe especificar tipo de cáncer "otro" cuando selecciona "OTRO"'
            })
        
        # Lista de TODOS los campos con choices
        campos_choices = [
            'cardiopatia_familiar',
            'hipertension_arterial_familiar', 
            'enfermedad_vascular_familiar',
            'endocrino_metabolico_familiar',
            'cancer_familiar',
            'tuberculosis_familiar',  
            'enfermedad_mental_familiar',
            'enfermedad_infecciosa_familiar',
            'malformacion_familiar'
        ]
        
        # Verificar que al menos un antecedente esté presente (solo en creación)
        if not self.instance:
            tiene_choice_activo = any(
                attrs.get(campo) and attrs.get(campo) != 'NO' 
                for campo in campos_choices
            )
            
            tiene_otros = bool(attrs.get('otros_antecedentes_familiares', '').strip())
            
            if not (tiene_choice_activo or tiene_otros):
                raise serializers.ValidationError(
                    "Debe proporcionar al menos un antecedente familiar"
                )
        
        # Validar coherencia: si hay "otros antecedentes", no puede estar vacío
        otros = attrs.get('otros_antecedentes_familiares', '').strip()
        if 'otros_antecedentes_familiares' in attrs and not otros:
            attrs['otros_antecedentes_familiares'] = ''
        
        return attrs


class ExamenesComplementariosSerializer(serializers.ModelSerializer):
    """Serializer para exámenes complementarios de pacientes"""
    
    # Campos calculados de solo lectura
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    paciente_cedula = serializers.CharField(source='paciente.cedula_pasaporte', read_only=True)
    
    class Meta:
        model = ExamenesComplementarios
        fields = "__all__"
        read_only_fields = [
            "id", "creado_por", "actualizado_por", 
            "fecha_creacion", "fecha_modificacion",
            "paciente_nombre", "paciente_cedula"  # ← Solo estos
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
                "No se pueden crear exámenes para un paciente inactivo"
            )
        return value
    
    def validate_pedido_examenes(self, value):
        """Validar choices de pedido de exámenes"""
        valid_choices = ['NO', 'SI']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_informe_examenes(self, value):
        """Validar choices de informe de exámenes"""
        valid_choices = ['NINGUNO', 'BIOMETRIA', 'QUIMICA_SANGUINEA', 'RAYOS_X', 'OTROS']
        if value and value not in valid_choices:
            raise serializers.ValidationError(
                f"Valor inválido. Debe ser uno de: {', '.join(valid_choices)}"
            )
        return value
    
    def validate_pedido_examenes_detalle(self, value):
        """Validar longitud de detalle de pedido"""
        if value and len(value) > 1000:
            raise serializers.ValidationError(
                "El campo 'detalle de exámenes solicitados' no puede exceder 1000 caracteres"
            )
        return value
    
    def validate_informe_examenes_detalle(self, value):
        """Validar longitud de detalle de informe"""
        if value and len(value) > 1000:
            raise serializers.ValidationError(
                "El campo 'resultados de exámenes' no puede exceder 1000 caracteres"
            )
        return value
    
    def validate(self, attrs):
        """Validaciones generales"""
        
        # Validar pedido de exámenes
        if attrs.get('pedido_examenes') == 'SI' and not attrs.get('pedido_examenes_detalle'):
            raise serializers.ValidationError({
                'pedido_examenes_detalle': 'Debe especificar los exámenes solicitados'
            })
        
        # Validar que pedido_examenes_detalle esté vacío si pedido_examenes es 'NO'
        if attrs.get('pedido_examenes') == 'NO' and attrs.get('pedido_examenes_detalle'):
            raise serializers.ValidationError({
                'pedido_examenes_detalle': 'No debe especificar detalles si no solicita exámenes'
            })
        
        # Validar informe de exámenes "OTROS"
        if attrs.get('informe_examenes') == 'OTROS' and not attrs.get('informe_examenes_detalle'):
            raise serializers.ValidationError({
                'informe_examenes_detalle': 'Debe especificar el tipo de examen cuando selecciona "Otros"'
            })
        
        # Validar que informe_examenes_detalle esté vacío si informe_examenes es 'NINGUNO'
        if attrs.get('informe_examenes') == 'NINGUNO' and attrs.get('informe_examenes_detalle'):
            raise serializers.ValidationError({
                'informe_examenes_detalle': 'No debe especificar resultados si no hay informe de exámenes'
            })
        
        # Validar que si hay informe, debe tener detalle
        if attrs.get('informe_examenes') and attrs.get('informe_examenes') != 'NINGUNO':
            if not attrs.get('informe_examenes_detalle'):
                raise serializers.ValidationError({
                    'informe_examenes_detalle': 'Debe detallar los resultados del examen'
                })
        
        return attrs
    

