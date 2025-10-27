# api/odontogram/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q

from api.odontogram.models import (
    AreaAfectada,
    Diagnostico,
    OpcionAtributoClinico,
    Paciente,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma,
    CategoriaDiagnostico,
    TipoAtributoClinico,
)

User = get_user_model()

# =============================================================================
# SERIALIZERS BÁSICOS Y CATÁLOGOS
# =============================================================================

class CategoriaDiagnosticoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaDiagnostico
        fields = '__all__'

class AreaAfectadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaAfectada
        fields = '__all__'

class TipoAtributoClinicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoAtributoClinico
        fields = '__all__'

class OpcionAtributoClinicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcionAtributoClinico
        fields = '__all__'

class DiagnosticoListSerializer(serializers.ModelSerializer):
    categoria = CategoriaDiagnosticoSerializer(read_only=True)
    class Meta:
        model = Diagnostico
        fields = '__all__'

class DiagnosticoDetailSerializer(serializers.ModelSerializer):
    categoria = CategoriaDiagnosticoSerializer(read_only=True)
    class Meta:
        model = Diagnostico
        fields = '__all__'

class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']

class PacienteBasicSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.ReadOnlyField()
    class Meta:
        model = Paciente
        fields = ['id', 'nombres', 'apellidos', 'nombre_completo', 'cedula', 'email', 'telefono']

# =============================================================================
# SERIALIZERS PARA DIAGNÓSTICO DENTAL
# =============================================================================

class DiagnosticoDentalListSerializer(serializers.ModelSerializer):
    diagnostico_nombre = serializers.CharField(source='diagnostico_catalogo.nombre', read_only=True)
    diagnostico_siglas = serializers.CharField(source='diagnostico_catalogo.siglas', read_only=True)
    diagnostico_key = serializers.CharField(source='diagnostico_catalogo.key', read_only=True)
    codigo_fdi = serializers.CharField(source='superficie.diente.codigo_fdi', read_only=True)
    superficie_nombre = serializers.CharField(source='superficie.get_nombre_display', read_only=True)
    odontologo_nombre = serializers.CharField(source='odontologo.get_full_name', read_only=True)
    class Meta:
        model = DiagnosticoDental
        fields = [
            'id', 'codigo_fdi', 'superficie_nombre',
            'diagnostico_nombre', 'diagnostico_siglas', 'diagnostico_key',
            'descripcion', 'estado_tratamiento', 'prioridad_efectiva',
            'fecha', 'odontologo_nombre', 'activo'
        ]

class DiagnosticoDentalDetailSerializer(serializers.ModelSerializer):
    diagnostico_info = serializers.SerializerMethodField()
    diente_info = serializers.SerializerMethodField()
    superficie_info = serializers.SerializerMethodField()
    odontologo_info = UserMinimalSerializer(source='odontologo', read_only=True)
    class Meta:
        model = DiagnosticoDental
        fields = [
            'id', 'diente_info', 'superficie_info',
            'diagnostico_info', 'descripcion',
            'atributos_clinicos', 'prioridad_asignada',
            'prioridad_efectiva', 'estado_tratamiento',
            'fecha', 'fecha_tratamiento', 'odontologo_info', 'activo'
        ]
        read_only_fields = ['id', 'fecha']
    def get_diagnostico_info(self, obj):
        return {
            'id': obj.diagnostico_catalogo.id,
            'key': obj.diagnostico_catalogo.key,
            'nombre': obj.diagnostico_catalogo.nombre,
            'siglas': obj.diagnostico_catalogo.siglas,
            'simbolo_color': obj.diagnostico_catalogo.simbolo_color,
            'prioridad_catalogo': obj.diagnostico_catalogo.prioridad,
        }
    def get_diente_info(self, obj):
        return {
            'codigo_fdi': obj.superficie.diente.codigo_fdi,
            'nombre': obj.superficie.diente.nombre,
            'ausente': obj.superficie.diente.ausente,
        }
    def get_superficie_info(self, obj):
        return {
            'nombre': obj.superficie.nombre,
            'nombre_display': obj.superficie.get_nombre_display(),
        }

class DiagnosticoDentalCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticoDental
        fields = [
            'diagnostico_catalogo', 'odontologo',
            'descripcion', 'atributos_clinicos',
            'prioridad_asignada', 'estado_tratamiento'
        ]

# =============================================================================
# SERIALIZERS PARA SUPERFICIE DENTAL
# =============================================================================

class SuperficieDentalListSerializer(serializers.ModelSerializer):
    diagnosticos_count = serializers.SerializerMethodField()
    diagnosticos = DiagnosticoDentalListSerializer(many=True, read_only=True)
    class Meta:
        model = SuperficieDental
        fields = ['id', 'nombre', 'diagnosticos_count', 'diagnosticos']
    def get_diagnosticos_count(self, obj):
        return obj.diagnosticos.filter(activo=True).count()

# =============================================================================
# SERIALIZERS PARA DIENTE
# =============================================================================

class DienteDetailSerializer(serializers.ModelSerializer):
    superficies = SuperficieDentalListSerializer(many=True, read_only=True)
    diagnosticos_total = serializers.SerializerMethodField()
    diagnosticos_criticos = serializers.SerializerMethodField()
    class Meta:
        model = Diente
        fields = [
            'id', 'codigo_fdi', 'nombre', 'ausente',
            'superficies', 'diagnosticos_total',
            'diagnosticos_criticos', 'fecha_creacion'
        ]
    def get_diagnosticos_total(self, obj):
        return DiagnosticoDental.objects.filter(
            superficie__diente=obj,
            activo=True
        ).count()
    def get_diagnosticos_criticos(self, obj):
        return DiagnosticoDental.objects.filter(
            superficie__diente=obj,
            activo=True
        ).filter(
            Q(prioridad_asignada__gte=4) |
            (Q(prioridad_asignada__isnull=True) &
             Q(diagnostico_catalogo__prioridad__gte=4))
        ).count()

# =============================================================================
# SERIALIZERS PARA PACIENTE
# =============================================================================

class PacienteDetailSerializer(serializers.ModelSerializer):
    dientes = DienteDetailSerializer(many=True, read_only=True)
    total_dientes = serializers.SerializerMethodField()
    total_diagnosticos = serializers.SerializerMethodField()
    edad = serializers.SerializerMethodField()
    class Meta:
        model = Paciente
        fields = [
            'id', 'nombres', 'apellidos', 'nombre_completo',
            'cedula', 'fecha_nacimiento', 'edad',
            'telefono', 'email', 'direccion',
            'dientes', 'total_dientes', 'total_diagnosticos',
            'fecha_registro', 'activo'
        ]
    def get_total_dientes(self, obj):
        return Diente.objects.filter(paciente=obj).count()
    def get_total_diagnosticos(self, obj):
        return DiagnosticoDental.objects.filter(
            superficie__diente__paciente=obj,
            activo=True
        ).count()
    def get_edad(self, obj):
        if not obj.fecha_nacimiento:
            return None
        from datetime import date
        today = date.today()
        return today.year - obj.fecha_nacimiento.year - (
            (today.month, today.day) < (obj.fecha_nacimiento.month, obj.fecha_nacimiento.day)
        )

# =============================================================================
# SERIALIZERS PARA CONFIGURACIÓN (FALTABA)
# =============================================================================

class OdontogramaConfigSerializer(serializers.Serializer):
    """Serializer para la configuración completa del odontograma"""
    categorias = CategoriaDiagnosticoSerializer(many=True, read_only=True)
    areas_afectadas = AreaAfectadaSerializer(many=True, read_only=True)
    tipos_atributos = TipoAtributoClinicoSerializer(many=True, read_only=True)

# =============================================================================
# SERIALIZERS PARA GUARDAR ODONTOGRAMA COMPLETO
# =============================================================================

class GuardarOdontogramaCompletoSerializer(serializers.Serializer):
    paciente_id = serializers.UUIDField()
    odontologo_id = serializers.IntegerField()
    odontograma_data = serializers.DictField(
        child=serializers.DictField(
            child=serializers.ListField()
        ),
        help_text="Estructura: {codigo_fdi: {superficie: [diagnosticos]}}"
    )
    def create(self, validated_data):
        from api.odontogram.services.odontogram_services import OdontogramaService
        service = OdontogramaService()
        return service.guardar_odontograma_completo(
            paciente_id=validated_data['paciente_id'],
            odontologo_id=validated_data['odontologo_id'],
            odontograma_data=validated_data['odontograma_data']
        )

# =============================================================================
# SERIALIZERS PARA HISTORIAL
# =============================================================================

class HistorialOdontogramaSerializer(serializers.ModelSerializer):
    odontologo_nombre = serializers.CharField(source='odontologo.get_full_name', read_only=True)
    tipo_cambio_display = serializers.CharField(source='get_tipo_cambio_display', read_only=True)
    class Meta:
        model = HistorialOdontograma
        fields = [
            'id', 'tipo_cambio', 'tipo_cambio_display',
            'descripcion', 'odontologo_nombre', 'fecha',
            'datos_anteriores', 'datos_nuevos'
        ]
        read_only_fields = ['id', 'fecha']
