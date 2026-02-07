from rest_framework import serializers
from api.odontogram.models import DiagnosticoDental, Diagnostico

class DiagnosticoCIESerializer(serializers.ModelSerializer):
    """Serializer para diagnósticos con información CIE-10"""
    
    # Información del diagnóstico del catálogo
    diagnostico_nombre = serializers.CharField(source='diagnostico_catalogo.nombre', read_only=True)
    diagnostico_siglas = serializers.CharField(source='diagnostico_catalogo.siglas', read_only=True)
    diagnostico_key = serializers.CharField(source='diagnostico_catalogo.key', read_only=True)
    
    # Códigos estándar
    codigo_icd10 = serializers.CharField(source='diagnostico_catalogo.codigo_icd10', read_only=True)
    codigo_cdt = serializers.CharField(source='diagnostico_catalogo.codigo_cdt', read_only=True)
    codigo_fhir = serializers.CharField(source='diagnostico_catalogo.codigo_fhir', read_only=True)
    
    # Información del diente
    codigo_fdi = serializers.CharField(source='superficie.diente.codigo_fdi', read_only=True)
    diente_nombre = serializers.CharField(source='superficie.diente.nombre', read_only=True)
    
    # Información de la superficie
    superficie_nombre = serializers.CharField(source='superficie.get_nombre_display', read_only=True)
    
    # Información del paciente
    paciente_id = serializers.UUIDField(source='superficie.diente.paciente.id', read_only=True)
    paciente_nombres = serializers.CharField(source='superficie.diente.paciente.nombres', read_only=True)
    paciente_apellidos = serializers.CharField(source='superficie.diente.paciente.apellidos', read_only=True)
    
    # Información del odontólogo
    odontologo_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = DiagnosticoDental
        fields = [
            'id',
            # Información del diagnóstico
            'diagnostico_nombre',
            'diagnostico_siglas',
            'diagnostico_key',
            'codigo_icd10',
            'codigo_cdt',
            'codigo_fhir',
            'descripcion',
            
            # Tipo de diagnóstico
            'tipo_diagnostico',
            
            # Información del diente
            'codigo_fdi',
            'diente_nombre',
            
            # Información de la superficie
            'superficie_nombre',
            
            # Información del paciente
            'paciente_id',
            'paciente_nombres',
            'paciente_apellidos',
            
            # Información del odontólogo
            'odontologo_nombre',
            
            # Fechas y estado
            'fecha',
            'fecha_tratamiento',
            'estado_tratamiento',
            'prioridad_efectiva',
            
            # Metadata
            'activo'
        ]
        read_only_fields = ['id', 'fecha']
    
    def get_odontologo_nombre(self, obj):
        if obj.odontologo:
            return f"{obj.odontologo.nombres} {obj.odontologo.apellidos}"
        return None