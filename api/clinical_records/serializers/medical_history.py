# api/patients/serializers/antecedentes_serializers.py
"""
Serializers COMPLETOS para Antecedentes Personales y Familiares
Incluyen TODOS los campos de los modelos actualizados
"""

from rest_framework import serializers
from api.patients.models.antecedentes_personales import AntecedentesPersonales
from api.patients.models.antecedentes_familiares import AntecedentesFamiliares


class AntecedentesPersonalesSerializer(serializers.ModelSerializer):
    """
    Serializer COMPLETO para antecedentes personales
    Incluye TODOS los campos del modelo actualizado
    """
    
    # Campos calculados de solo lectura (propiedades del modelo)
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    paciente_cedula = serializers.CharField(source='paciente.cedula_pasaporte', read_only=True)
    tiene_condiciones_importantes = serializers.BooleanField(read_only=True)
    tiene_antecedentes_criticos = serializers.BooleanField(read_only=True)
    tiene_alergias = serializers.BooleanField(read_only=True)
    resumen_alergias = serializers.CharField(read_only=True)
    resumen_condiciones = serializers.CharField(read_only=True)
    lista_antecedentes = serializers.ListField(read_only=True)
    total_antecedentes = serializers.IntegerField(read_only=True)
    riesgo_visual = serializers.CharField(read_only=True)
    exigencias_quirurgicas = serializers.ListField(read_only=True)
    
    class Meta:
        model = AntecedentesPersonales
        fields = [
            # IDs y relaciones
            'id',
            'paciente',
            'paciente_nombre',
            'paciente_cedula',
            
            # 1. ALERGIA ANTIBIÓTICO
            'alergia_antibiotico',
            'alergia_antibiotico_otro',
            
            # 2. ALERGIA ANESTESIA
            'alergia_anestesia',
            'alergia_anestesia_otro',
            
            # 3. HEMORRAGIAS
            'hemorragias',
            'hemorragias_detalle',
            
            # 4. VIH / SIDA
            'vih_sida',
            'vih_sida_otro',
            
            # 5. TUBERCULOSIS
            'tuberculosis',
            'tuberculosis_otro',
            
            # 6. ASMA
            'asma',
            'asma_otro',
            
            # 7. DIABETES
            'diabetes',
            'diabetes_otro',
            
            # 8. HIPERTENSIÓN ARTERIAL
            'hipertension_arterial',
            'hipertension_arterial_otro',
            
            # 9. ENFERMEDAD CARDIACA
            'enfermedad_cardiaca',
            'enfermedad_cardiaca_otro',
            
            # 10. OTROS ANTECEDENTES
            'otros_antecedentes_personales',
            
            # HÁBITOS Y OBSERVACIONES
            'habitos',
            'observaciones',
            
            # Campos calculados
            'tiene_condiciones_importantes',
            'tiene_antecedentes_criticos',
            'tiene_alergias',
            'resumen_alergias',
            'resumen_condiciones',
            'lista_antecedentes',
            'total_antecedentes',
            'riesgo_visual',
            'exigencias_quirurgicas',
            
            # Metadata
            'activo',
            'creado_por',
            'actualizado_por',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = [
            'id',
            'paciente_nombre',
            'paciente_cedula',
            'tiene_condiciones_importantes',
            'tiene_antecedentes_criticos',
            'tiene_alergias',
            'resumen_alergias',
            'resumen_condiciones',
            'lista_antecedentes',
            'total_antecedentes',
            'riesgo_visual',
            'exigencias_quirurgicas',
            'creado_por',
            'actualizado_por',
            'fecha_creacion',
            'fecha_modificacion',
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
    
    def validate(self, attrs):
        """Validaciones generales"""
        
        # Lista de todos los campos con sus correspondientes _otro
        campos_validar = [
            ('alergia_antibiotico', 'alergia_antibiotico_otro'),
            ('alergia_anestesia', 'alergia_anestesia_otro'),
            ('vih_sida', 'vih_sida_otro'),
            ('tuberculosis', 'tuberculosis_otro'),
            ('asma', 'asma_otro'),
            ('diabetes', 'diabetes_otro'),
            ('hipertension_arterial', 'hipertension_arterial_otro'),
            ('enfermedad_cardiaca', 'enfermedad_cardiaca_otro'),
        ]
        
        # Validar todos los campos con _otro
        for campo_principal, campo_otro in campos_validar:
            valor_principal = attrs.get(campo_principal)
            valor_otro = attrs.get(campo_otro, '')
            
            # Si es OTRO, el campo _otro es requerido
            if valor_principal == 'OTRO' and not valor_otro:
                raise serializers.ValidationError({
                    campo_otro: f'Debe especificar detalles cuando selecciona "OTRO"'
                })
            
            # Si NO es OTRO, el campo _otro debe estar vacío
            if valor_principal and valor_principal != 'OTRO' and valor_otro:
                raise serializers.ValidationError({
                    campo_otro: f'No debe especificar detalles cuando no selecciona "OTRO"'
                })
        
        # Validación especial para hemorragias
        if attrs.get('hemorragias') == 'SI' and not attrs.get('hemorragias_detalle'):
            raise serializers.ValidationError({
                'hemorragias_detalle': 'Debe especificar detalles de hemorragias'
            })
        elif attrs.get('hemorragias') == 'NO' and attrs.get('hemorragias_detalle'):
            raise serializers.ValidationError({
                'hemorragias_detalle': 'No debe especificar detalles cuando no hay hemorragias'
            })
        
        return attrs


class AntecedentesFamiliaresSerializer(serializers.ModelSerializer):
    """
    Serializer COMPLETO para antecedentes familiares
    Incluye TODOS los campos del modelo actualizado
    """
    
    # Campos calculados de solo lectura (propiedades del modelo)
    paciente_nombre = serializers.CharField(source='paciente.apellidos', read_only=True)
    paciente_cedula = serializers.CharField(source='paciente.cedula_pasaporte', read_only=True)
    tiene_antecedentes_importantes = serializers.BooleanField(read_only=True)
    lista_antecedentes = serializers.ListField(read_only=True)
    resumen_antecedentes = serializers.CharField(read_only=True)
    
    class Meta:
        model = AntecedentesFamiliares
        fields = [
            # IDs y relaciones
            'id',
            'paciente',
            'paciente_nombre',
            'paciente_cedula',
            
            # 1. CARDIOPATÍA
            'cardiopatia_familiar',
            'cardiopatia_familiar_otro',
            
            # 2. HIPERTENSIÓN ARTERIAL
            'hipertension_arterial_familiar',
            'hipertension_arterial_familiar_otro',
            
            # 3. ENFERMEDAD C. VASCULAR
            'enfermedad_vascular_familiar',
            'enfermedad_vascular_familiar_otro',
            
            # 4. ENDÓCRINO METABÓLICO
            'endocrino_metabolico_familiar',
            'endocrino_metabolico_familiar_otro',
            
            # 5. CÁNCER
            'cancer_familiar',
            'cancer_familiar_otro',
            'tipo_cancer',
            'tipo_cancer_otro',
            
            # 6. TUBERCULOSIS
            'tuberculosis_familiar',
            'tuberculosis_familiar_otro',
            
            # 7. ENFERMEDAD MENTAL
            'enfermedad_mental_familiar',
            'enfermedad_mental_familiar_otro',
            
            # 8. ENFERMEDAD INFECCIOSA
            'enfermedad_infecciosa_familiar',
            'enfermedad_infecciosa_familiar_otro',
            
            # 9. MALFORMACIÓN
            'malformacion_familiar',
            'malformacion_familiar_otro',
            
            # 10. OTROS
            'otros_antecedentes_familiares',
            
            
            
            # Campos calculados
            'tiene_antecedentes_importantes',
            'lista_antecedentes',
            'resumen_antecedentes',
            
            # Metadata
            'activo',
            'creado_por',
            'actualizado_por',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = [
            'id',
            'paciente_nombre',
            'paciente_cedula',
            'tiene_antecedentes_importantes',
            'lista_antecedentes',
            'resumen_antecedentes',
            'creado_por',
            'actualizado_por',
            'fecha_creacion',
            'fecha_modificacion',
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
    
    def validate(self, attrs):
        """Validaciones generales"""
        
        # Validar campos "OTRO"
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
        
        for campo_principal, campo_otro in campos_validar:
            valor_principal = attrs.get(campo_principal)
            valor_otro = attrs.get(campo_otro, '')
            
            if valor_principal == 'OTRO' and not valor_otro:
                raise serializers.ValidationError({
                    campo_otro: f'Debe especificar el familiar cuando selecciona "Otro"'
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


# ============================================================================
# SERIALIZERS WRITABLES PARA HISTORIAL CLÍNICO (NESTED)
# ============================================================================

class WritableAntecedentesPersonalesSerializer(AntecedentesPersonalesSerializer):
    """
    Serializer writable para antecedentes personales anidados en historial clínico
    """
    
    class Meta(AntecedentesPersonalesSerializer.Meta):
        # Heredar todos los campos del serializer base
        fields = AntecedentesPersonalesSerializer.Meta.fields
        # Hacer read_only los campos de metadata del BaseModel
        read_only_fields = [
            'id',
            'paciente_nombre',
            'paciente_cedula',
            'tiene_condiciones_importantes',
            'tiene_antecedentes_criticos',
            'tiene_alergias',
            'resumen_alergias',
            'resumen_condiciones',
            'lista_antecedentes',
            'total_antecedentes',
            'riesgo_visual',
            'exigencias_quirurgicas',
            'creado_por',
            'actualizado_por',
            'fecha_creacion',
            'fecha_modificacion',
            'activo',
        ]


class WritableAntecedentesFamiliaresSerializer(AntecedentesFamiliaresSerializer):
    """
    Serializer writable para antecedentes familiares anidados en historial clínico
    """
    
    class Meta(AntecedentesFamiliaresSerializer.Meta):
        # Heredar todos los campos del serializer base
        fields = AntecedentesFamiliaresSerializer.Meta.fields
        # Hacer read_only los campos de metadata del BaseModel
        read_only_fields = [
            'id',
            'paciente_nombre',
            'paciente_cedula',
            'tiene_antecedentes_importantes',
            'lista_antecedentes',
            'resumen_antecedentes',
            'creado_por',
            'actualizado_por',
            'fecha_creacion',
            'fecha_modificacion',
            'activo',
        ]