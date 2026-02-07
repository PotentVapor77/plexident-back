# api/odontogram/serializers.py
from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q


from api.odontogram.models import (
    AreaAfectada,
    Diagnostico,
    IndicadoresSaludBucal,
    IndiceCariesSnapshot,
    OpcionAtributoClinico,
    Paciente,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma,
    CategoriaDiagnostico,
    TipoAtributoClinico,
)
from api.odontogram.constants import ESCALA_CALCULO, ESCALA_GINGIVITIS, ESCALA_PLACA, NIVELES_FLUOROSIS, NIVELES_PERIODONTAL, TIPOS_OCLUSION
from api.odontogram.services.piezas_service import PiezasIndiceService    
import logging
logger = logging.getLogger(__name__)
User = get_user_model()

# =============================================================================
# SERIALIZERS BÁSICOS Y CATÁLOGOS
# =============================================================================

class CategoriaDiagnosticoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaDiagnostico
        fields = '__all__'

class DiagnosticoDentalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnostico
        fields = '__all__'

class AreaAfectadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaAfectada
        fields = '__all__'
class OpcionAtributoClinicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcionAtributoClinico
        fields = ['id', 'key', 'nombre', 'prioridad', 'orden', 'activo']

class TipoAtributoClinicoSerializer(serializers.ModelSerializer):
    opciones = OpcionAtributoClinicoSerializer(many=True, read_only=True)

    class Meta:
        model = TipoAtributoClinico
        fields = ['id', 'key', 'nombre', 'descripcion', 'activo', 'opciones']





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
        fields = ['id', 'nombres', 'apellidos', 'correo']


class PacienteBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = [
            'id', 'nombres', 'apellidos',
    'cedula_pasaporte', 'sexo', 'fecha_nacimiento',
    'telefono', 'correo', 'direccion'
        ]


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


class DiagnosticoDentalSerializer(serializers.ModelSerializer):
    """Serializer para diagnósticos con color_hex y priority"""
    
    color_hex = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    procedimientoId = serializers.SerializerMethodField()
    siglas = serializers.SerializerMethodField()
    
    class Meta:
        model = DiagnosticoDental
        fields = [
            'id',
            'procedimientoId',  # ← key del diagnostico
            'color_hex',         # ← CRÍTICO
            'priority',          # ← CRÍTICO
            'siglas',
            'tipo_registro',
            'estado_tratamiento',
            'atributos_clinicos',
        ]
    
    def get_color_hex(self, obj):
        return obj.color_hex
    
    def get_priority(self, obj):
        return obj.priority
    
    def get_procedimientoId(self, obj):
        return obj.diagnostico_catalogo.key
    
    def get_siglas(self, obj):
        return obj.diagnostico_catalogo.siglas


class SuperficieDentalSerializer(serializers.ModelSerializer):
    """Serializer para superficies con diagnosticos"""
    
    diagnosticos = DiagnosticoDentalSerializer(many=True, read_only=True)
    
    class Meta:
        model = SuperficieDental
        fields = ['id', 'nombre', 'codigo_fhir_superficie', 'diagnosticos']


class DienteSerializer(serializers.ModelSerializer):
    """
    Serializer para Diente - CÓDIGO_FDI COMO ID PRINCIPAL
    """
    
    superficies = SuperficieDentalSerializer(many=True, read_only=True)
    posicion_arcada = serializers.SerializerMethodField()
    posicion_cuadrante = serializers.SerializerMethodField()
    lado_arcada = serializers.SerializerMethodField()
    
    class Meta:
        model = Diente
        fields = [
            'codigo_fdi',           # ← ID PRINCIPAL para frontend (nombre en GLB)
            'numero_3d',            # ← ID secundario
            'nombre',
            'ausente',              # ← CRÍTICO (determina si diente ausente)
            'razon_ausencia',
            'movilidad',            # ← Formulario 033
            'recesion_gingival',    # ← Formulario 033
            'tipo_denticion',
            'posicion_arcada',      # ← Propiedad derivada
            'posicion_cuadrante',   # ← Propiedad derivada
            'lado_arcada',          # ← Propiedad derivada
            'superficies',          # ← Diagnósticos anidados
        ]
    
    def get_posicion_arcada(self, obj):
        return obj.posicion_arcada
    
    def get_posicion_cuadrante(self, obj):
        return obj.posicion_cuadrante
    
    def get_lado_arcada(self, obj):
        return obj.lado_arcada


class OdontogramaResponseSerializer(serializers.Serializer):
    """
    Respuesta completa del odontograma para frontend 3D
    Estructura: {codigo_fdi: {...}}
    """
    
    paciente_id = serializers.SerializerMethodField()
    dientes = serializers.SerializerMethodField()
    
    def get_paciente_id(self, data):
        return data.get('paciente_id')
    
    def get_dientes(self, data):
        # Estructura: {codigo_fdi: diente_data}
        dientes_dict = {}
        dientes = data.get('dientes', [])
        
        for diente_data in dientes:
            codigo_fdi = diente_data['codigo_fdi']
            dientes_dict[codigo_fdi] = diente_data
        
        return dientes_dict

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
            'id', 'nombres', 'apellidos',
            'cedula_pasaporte','sexo', 'fecha_nacimiento', 'edad',
            'telefono', 'correo', 'direccion',
            'dientes', 'total_dientes', 'total_diagnosticos',
            'activo'
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
# SERIALIZERS PARA CONFIGURACIÓN
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


class OpcionAtributoSerializer(serializers.Serializer):
    key = serializers.CharField()
    nombre = serializers.CharField()
    prioridad = serializers.IntegerField(allow_null=True)
    orden = serializers.IntegerField()


class TipoAtributoConOpcionesSerializer(serializers.Serializer):
    key = serializers.CharField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField()
    tipo_input = serializers.CharField(default='select')
    requerido = serializers.BooleanField(default=False)
    opciones = OpcionAtributoSerializer(many=True, read_only=True)


class DiagnosticoListSerializer(serializers.ModelSerializer):
    categoria = CategoriaDiagnosticoSerializer(read_only=True)
    atributos_relacionados = serializers.SerializerMethodField()
    
    class Meta:
        model = Diagnostico
        fields = '__all__'
    
    def get_atributos_relacionados(self, obj):
        """
        Obtiene los atributos clínicos relacionados al diagnóstico
        desde la tabla intermedia DiagnosticoAtributoClinico
        """
        from api.odontogram.models import DiagnosticoAtributoClinico
        
        # Obtener relaciones de este diagnóstico
        relaciones = DiagnosticoAtributoClinico.objects.filter(
            diagnostico=obj
        ).select_related('tipo_atributo').prefetch_related('tipo_atributo__opciones')
        
        atributos = []
        for rel in relaciones:
            tipo_attr = rel.tipo_atributo
            
            # Obtener opciones activas ordenadas
            opciones = tipo_attr.opciones.filter(activo=True).order_by('orden')
            
            atributos.append({
                'key': tipo_attr.key,
                'nombre': tipo_attr.nombre,
                'descripcion': tipo_attr.descripcion,
                'tipo_input': 'select',  # Puedes hacerlo dinámico si tienes un campo en TipoAtributoClinico
                'requerido': rel.requerido if hasattr(rel, 'requerido') else False,
                'opciones': [
                    {
                        'key': opc.key,
                        'nombre': opc.nombre,
                        'prioridad': opc.prioridad,
                        'orden': opc.orden,
                    }
                    for opc in opciones
                ]
            })
        
        return atributos

# =============================================================================
# SERIALIZERS PARA HISTORIAL
# =============================================================================

class HistorialOdontogramaSerializer(serializers.ModelSerializer):
    odontologo_nombre = serializers.SerializerMethodField()
    paciente_nombre = serializers.SerializerMethodField() 
    tipo_cambio_display = serializers.CharField(source='get_tipo_cambio_display', read_only=True)
    
    class Meta:
        model = HistorialOdontograma
        fields = [
            'id', 'tipo_cambio', 'tipo_cambio_display',
            'descripcion', 'odontologo_nombre','paciente_nombre', 'fecha',
            'datos_anteriores', 'datos_nuevos', 'version_id'
        ]
        read_only_fields = ['id', 'fecha']
    
    def get_odontologo_nombre(self, obj):
        if obj.odontologo:
            return f"{obj.odontologo.nombres} {obj.odontologo.apellidos}"
        return "N/A"
    def get_paciente_nombre(self, obj):
        """Obtiene el nombre del paciente desde el diente"""
        if obj.diente and obj.diente.paciente:
            paciente = obj.diente.paciente
            return f"{paciente.nombres} {paciente.apellidos}"
        return None
    
class WritableIndiceCariesSnapshotSerializer(serializers.ModelSerializer):
    """
    Serializer writable para anidación en historial clínico
    """
    
    class Meta:
        model = IndiceCariesSnapshot
        fields = '__all__'
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion', 'activo']
    
    def validate(self, data):
        """Validaciones personalizadas"""
        # Validar que al menos un índice tenga valor
        indices_componentes = [
            'cpo_c', 'cpo_p', 'cpo_o',
            'ceo_c', 'ceo_e', 'ceo_o'
        ]
        
        if not any(data.get(field) for field in indices_componentes if data.get(field) is not None):
            raise serializers.ValidationError(
                'Debe proporcionar al menos un valor de índice'
            )
        
        # Validar que no haya valores negativos
        for field in indices_componentes:
            if data.get(field) is not None and data[field] < 0:
                raise serializers.ValidationError(
                    f'El valor de {field} no puede ser negativo'
                )
        
        return data
    
    def create(self, validated_data):
        """Override create para manejar campos calculados"""
        # Calcular totales si no se proporcionan
        if 'cpo_total' not in validated_data:
            validated_data['cpo_total'] = (
                validated_data.get('cpo_c', 0) +
                validated_data.get('cpo_p', 0) +
                validated_data.get('cpo_o', 0)
            )
        
        if 'ceo_total' not in validated_data:
            validated_data['ceo_total'] = (
                validated_data.get('ceo_c', 0) +
                validated_data.get('ceo_e', 0) +
                validated_data.get('ceo_o', 0)
            )
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Override update para recalcular totales"""
        # Actualizar campos manualmente para recalcular totales
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Recalcular totales
        instance.cpo_total = instance.cpo_c + instance.cpo_p + instance.cpo_o
        instance.ceo_total = instance.ceo_c + instance.ceo_e + instance.ceo_o
        
        instance.save()
        return instance
class IndiceCariesSnapshotSerializer(serializers.ModelSerializer):
    """
    Serializer base (Read-only) para índices de caries
    """
    
    creado_por_nombre = serializers.SerializerMethodField()
    paciente_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = IndiceCariesSnapshot
        fields = [
            'id',
            'paciente',
            'paciente_nombre',
            'version_id',
            'fecha_evaluacion',
            'observaciones',
            'creado_por',
            'creado_por_nombre',
            'actualizado_por',
            'fecha_creacion',
            'fecha_modificacion',
            # Índices CPO
            'cpo_c',
            'cpo_p',
            'cpo_o',
            'cpo_total',
            # Índices ceo
            'ceo_c',
            'ceo_e',
            'ceo_o',
            'ceo_total',
            'activo'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']
    
    def get_creado_por_nombre(self, obj):
        if obj.creado_por:
            return f"{obj.creado_por.nombres} {obj.creado_por.apellidos}"
        return None
    
    def get_paciente_nombre(self, obj):
        if obj.paciente:
            return f"{obj.paciente.nombres} {obj.paciente.apellidos}"
        return None
    
    def validate(self, data):
        """Validaciones personalizadas"""
        # Validar que los totales sean consistentes (si se proporcionan componentes)
        if 'cpo_c' in data or 'cpo_p' in data or 'cpo_o' in data:
            cpo_c = data.get('cpo_c', getattr(self.instance, 'cpo_c', 0) if self.instance else 0)
            cpo_p = data.get('cpo_p', getattr(self.instance, 'cpo_p', 0) if self.instance else 0)
            cpo_o = data.get('cpo_o', getattr(self.instance, 'cpo_o', 0) if self.instance else 0)
            data['cpo_total'] = cpo_c + cpo_p + cpo_o
        
        if 'ceo_c' in data or 'ceo_e' in data or 'ceo_o' in data:
            ceo_c = data.get('ceo_c', getattr(self.instance, 'ceo_c', 0) if self.instance else 0)
            ceo_e = data.get('ceo_e', getattr(self.instance, 'ceo_e', 0) if self.instance else 0)
            ceo_o = data.get('ceo_o', getattr(self.instance, 'ceo_o', 0) if self.instance else 0)
            data['ceo_total'] = ceo_c + ceo_e + ceo_o
        
        return data


class WritableIndiceCariesSnapshotSerializer(serializers.ModelSerializer):
    """
    Serializer writable para anidación en historial clínico
    """
    
    class Meta:
        model = IndiceCariesSnapshot
        fields = [
            'id',
            'paciente',
            'version_id',
            'fecha_evaluacion',
            'observaciones',
            'creado_por',
            # Índices CPO
            'cpo_c',
            'cpo_p',
            'cpo_o',
            'cpo_total',
            # Índices ceo
            'ceo_c',
            'ceo_e',
            'ceo_o',
            'ceo_total'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion', 'activo']
    
    def validate(self, data):
        """Validaciones personalizadas"""
        # Validar que al menos un índice tenga valor
        indices_componentes = [
            'cpo_c', 'cpo_p', 'cpo_o',
            'ceo_c', 'ceo_e', 'ceo_o'
        ]
        
        if not any(data.get(field) for field in indices_componentes if data.get(field) is not None):
            raise serializers.ValidationError(
                'Debe proporcionar al menos un valor de índice'
            )
        
        # Validar que no haya valores negativos
        for field in indices_componentes:
            if data.get(field) is not None and data[field] < 0:
                raise serializers.ValidationError(
                    f'El valor de {field} no puede ser negativo'
                )
        
        return data


class WritableIndiceCariesSnapshotSerializer(serializers.ModelSerializer):
    """
    Serializer writable para anidación en historial clínico
    """
    
    class Meta:
        model = IndiceCariesSnapshot
        fields = '__all__'
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion', 'activo']
    
    def validate(self, data):
        """Validaciones personalizadas"""
        # Validar que al menos un índice tenga valor
        indices_componentes = [
            'cpo_c', 'cpo_p', 'cpo_o',
            'ceo_c', 'ceo_e', 'ceo_o'
        ]
        
        if not any(data.get(field) for field in indices_componentes if data.get(field) is not None):
            raise serializers.ValidationError(
                'Debe proporcionar al menos un valor de índice'
            )
        
        # Validar que no haya valores negativos
        for field in indices_componentes:
            if data.get(field) is not None and data[field] < 0:
                raise serializers.ValidationError(
                    f'El valor de {field} no puede ser negativo'
                )
        
        return data
    
    def create(self, validated_data):
        """Override create para manejar campos calculados"""
        # Calcular totales si no se proporcionan
        if 'cpo_total' not in validated_data:
            validated_data['cpo_total'] = (
                validated_data.get('cpo_c', 0) +
                validated_data.get('cpo_p', 0) +
                validated_data.get('cpo_o', 0)
            )
        
        if 'ceo_total' not in validated_data:
            validated_data['ceo_total'] = (
                validated_data.get('ceo_c', 0) +
                validated_data.get('ceo_e', 0) +
                validated_data.get('ceo_o', 0)
            )
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Override update para recalcular totales"""
        # Actualizar campos manualmente para recalcular totales
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Recalcular totales
        instance.cpo_total = instance.cpo_c + instance.cpo_p + instance.cpo_o
        instance.ceo_total = instance.ceo_c + instance.ceo_e + instance.ceo_o
        
        instance.save()
        return instance


class IndiceCariesSnapshotDetailSerializer(IndiceCariesSnapshotSerializer):
    """
    Serializer detallado con información adicional
    """
    
    interpretacion_cpo = serializers.SerializerMethodField()
    interpretacion_ceo = serializers.SerializerMethodField()
    resumen_estado = serializers.SerializerMethodField()
    
    class Meta(IndiceCariesSnapshotSerializer.Meta):
        fields = IndiceCariesSnapshotSerializer.Meta.fields + [
            'interpretacion_cpo',
            'interpretacion_ceo',
            'resumen_estado'
        ]
    
    def get_interpretacion_cpo(self, obj):
        """Interpretación del índice CPO según OMS"""
        if obj.cpo_total == 0:
            return "Excelente salud dental (CPO = 0)"
        elif obj.cpo_total <= 2:
            return "Baja prevalencia de caries (CPO 1-2)"
        elif obj.cpo_total <= 4:
            return "Moderada prevalencia de caries (CPO 3-4)"
        elif obj.cpo_total <= 6:
            return "Alta prevalencia de caries (CPO 5-6)"
        else:
            return "Muy alta prevalencia de caries (CPO > 6)"
    
    def get_interpretacion_ceo(self, obj):
        """Interpretación del índice ceo según OMS"""
        if obj.ceo_total == 0:
            return "Excelente salud dental temporal (ceo = 0)"
        elif obj.ceo_total <= 2:
            return "Baja prevalencia de caries (ceo 1-2)"
        elif obj.ceo_total <= 4:
            return "Moderada prevalencia de caries (ceo 3-4)"
        elif obj.ceo_total <= 6:
            return "Alta prevalencia de caries (ceo 5-6)"
        else:
            return "Muy alta prevalencia de caries (ceo > 6)"
    
    def get_resumen_estado(self, obj):
        """Resumen del estado de salud dental"""
        if obj.cpo_total == 0 and obj.ceo_total == 0:
            return "Óptimo - Sin caries diagnosticadas"
        
        resumen = []
        if obj.cpo_total > 0:
            resumen.append(f"CPO: {obj.cpo_total} (C:{obj.cpo_c} P:{obj.cpo_p} O:{obj.cpo_o})")
        if obj.ceo_total > 0:
            resumen.append(f"ceo: {obj.ceo_total} (c:{obj.ceo_c} e:{obj.ceo_e} o:{obj.ceo_o})")
        
        return " | ".join(resumen)


class IndicadoresSaludBucalSerializer(serializers.ModelSerializer):
    """
    Serializer base para Indicadores de Salud Bucal
    Contiene solo los campos del modelo
    """
    
    class Meta:
        model = IndicadoresSaludBucal
        fields = "__all__"
        read_only_fields = (
            "id", 
            "fecha", 
            "creado_por", 
            "actualizado_por",
            "ohi_promedio_placa", 
            "ohi_promedio_calculo",
            "gi_promedio_gingivitis", 
            "informacion_calculo",
            "piezas_usadas_en_registro"
            
        )
    
    def validate(self, data):
        """
        Validación personalizada para los indicadores
        """
        # Validar rangos de valores por pieza
        for pieza in ['16', '11', '26', '36', '31', '46']:
            placa_field = f'pieza_{pieza}_placa'
            calculo_field = f'pieza_{pieza}_calculo'
            gingivitis_field = f'pieza_{pieza}_gingivitis'
            
            if placa_field in data and data[placa_field] is not None:
                if not 0 <= data[placa_field] <= 3:
                    raise serializers.ValidationError(
                        {placa_field: f"Valor debe estar entre 0 y 3, actual: {data[placa_field]}"}
                    )
            
            if calculo_field in data and data[calculo_field] is not None:
                if not 0 <= data[calculo_field] <= 3:
                    raise serializers.ValidationError(
                        {calculo_field: f"Valor debe estar entre 0 y 3, actual: {data[calculo_field]}"}
                    )
            
            if gingivitis_field in data and data[gingivitis_field] is not None:
                if not 0 <= data[gingivitis_field] <= 3:
                    raise serializers.ValidationError(
                        {gingivitis_field: f"Valor debe estar entre 0 y 3, actual: {data[gingivitis_field]}"}
                    )
        
        return data


class IndicadoresSaludBucalListSerializer(IndicadoresSaludBucalSerializer):
    """
    Serializer para listar indicadores (campos mínimos)
    """
    
    paciente_nombre_completo = serializers.SerializerMethodField()
    creado_por_nombre = serializers.SerializerMethodField()
    resumen_higiene = serializers.SerializerMethodField()
    resumen_gingival = serializers.SerializerMethodField()
    
    class Meta(IndicadoresSaludBucalSerializer.Meta):
        fields = [
            'id',
            'paciente_nombre_completo',
            'fecha',
            'enfermedad_periodontal',
            'nivel_gingivitis',
            'ohi_promedio_placa',
            'ohi_promedio_calculo',
            'gi_promedio_gingivitis',
            'resumen_higiene',
            'resumen_gingival',
            'creado_por_nombre',
            'activo'
        ]
    
    def get_paciente_nombre_completo(self, obj):
        if obj.paciente:
            return f"{obj.paciente.nombres} {obj.paciente.apellidos}"
        return None
    
    def get_creado_por_nombre(self, obj):
        if obj.creado_por:
            return f"{obj.creado_por.nombres} {obj.creado_por.apellidos}"
        return "N/A"
    
    def get_resumen_higiene(self, obj):
        """Calcula resumen de higiene basado en promedios"""
        if obj.ohi_promedio_placa is not None and obj.ohi_promedio_calculo is not None:
            total = obj.ohi_promedio_placa + obj.ohi_promedio_calculo
            if total <= 0.6:
                return "Excelente"
            elif total <= 1.2:
                return "Bueno"
            elif total <= 1.8:
                return "Regular"
            elif total <= 3.0:
                return "Deficiente"
            else:
                return "Pésimo"
        return "Sin datos"
    
    def get_resumen_gingival(self, obj):
        """Resumen de salud gingival"""
        if obj.gi_promedio_gingivitis is not None:
            if obj.gi_promedio_gingivitis <= 0.1:
                return "Normal"
            elif obj.gi_promedio_gingivitis <= 1.0:
                return "Leve"
            elif obj.gi_promedio_gingivitis <= 2.0:
                return "Moderada"
            else:
                return "Severa"
        return "Sin datos"


class IndicadoresSaludBucalDetailSerializer(IndicadoresSaludBucalSerializer):
    """
    Serializer detallado para indicadores con toda la información
    """
    
    paciente_info = serializers.SerializerMethodField()
    creado_por_info = serializers.SerializerMethodField()
    actualizado_por_info = serializers.SerializerMethodField()
    
    # Campos calculados
    calculos_completos = serializers.SerializerMethodField()
    valores_por_pieza = serializers.SerializerMethodField()
    escalas_referencia = serializers.SerializerMethodField()
    
    # Información de diagnóstico con descripciones
    enfermedad_periodontal_display = serializers.SerializerMethodField()
    tipo_oclusion_display = serializers.SerializerMethodField()
    nivel_fluorosis_display = serializers.SerializerMethodField()
    nivel_gingivitis_display = serializers.SerializerMethodField()
    informacion_piezas_usadas = serializers.SerializerMethodField()
    class Meta:
        model = IndicadoresSaludBucal
        fields = [
            # Información básica
            'id', 'fecha', 'fecha_modificacion', 'activo',
            
            # Información del paciente
            'paciente', 'paciente_info',
            
            # Auditoría
            'creado_por', 'creado_por_info',
            'actualizado_por', 'actualizado_por_info',
            'eliminado_por', 'fecha_eliminacion',
            
            # Campos de diagnóstico
            'enfermedad_periodontal', 'enfermedad_periodontal_display',
            'tipo_oclusion', 'tipo_oclusion_display',
            'nivel_fluorosis', 'nivel_fluorosis_display',
            'nivel_gingivitis', 'nivel_gingivitis_display',
            'observaciones',
            
            # Valores por pieza
            # Placa
            'pieza_16_placa', 'pieza_11_placa', 'pieza_26_placa',
            'pieza_36_placa', 'pieza_31_placa', 'pieza_46_placa',
            
            # Cálculo
            'pieza_16_calculo', 'pieza_11_calculo', 'pieza_26_calculo',
            'pieza_36_calculo', 'pieza_31_calculo', 'pieza_46_calculo',
            
            # Gingivitis
            'pieza_16_gingivitis', 'pieza_11_gingivitis', 'pieza_26_gingivitis',
            'pieza_36_gingivitis', 'pieza_31_gingivitis', 'pieza_46_gingivitis',
            
            # Promedios
            'ohi_promedio_placa', 'ohi_promedio_calculo', 'gi_promedio_gingivitis',
            
            # Información de cálculo (JSON)
            'informacion_calculo',
            
            # Información de piezas
            'informacion_piezas_usadas',
            'piezas_usadas_en_registro',
            # Campos calculados
            'valores_por_pieza',
            'calculos_completos',
            'escalas_referencia'
        ]
    
    def get_paciente_info(self, obj):
        """Información completa del paciente"""
        if obj.paciente:
            return {
                'id': str(obj.paciente.id),
                'nombres': obj.paciente.nombres,
                'apellidos': obj.paciente.apellidos,
                'nombre_completo': f"{obj.paciente.nombres} {obj.paciente.apellidos}",
                'cedula_pasaporte': obj.paciente.cedula_pasaporte,
                'edad': obj.paciente.edad if hasattr(obj.paciente, 'edad') else None,
                'sexo': obj.paciente.sexo
            }
        return None
    
    def get_creado_por_info(self, obj):
        """Información del usuario creador"""
        if obj.creado_por:
            return {
                'id': obj.creado_por.id,
                'nombre_completo': f"{obj.creado_por.nombres} {obj.creado_por.apellidos}",
                'nombres': obj.creado_por.nombres,
                'apellidos': obj.creado_por.apellidos,
                'correo': obj.creado_por.correo
            }
        return None
    
    def get_actualizado_por_info(self, obj):
        """Información del usuario que actualizó"""
        if obj.actualizado_por:
            return {
                'id': obj.actualizado_por.id,
                'nombre_completo': f"{obj.actualizado_por.nombres} {obj.actualizado_por.apellidos}",
                'nombres': obj.actualizado_por.nombres,
                'apellidos': obj.actualizado_por.apellidos,
                'correo': obj.actualizado_por.correo
            }
        return None
    
    def get_enfermedad_periodontal_display(self, obj):
        """Descripción de enfermedad periodontal"""
        if obj.enfermedad_periodontal:
            return NIVELES_PERIODONTAL.get(obj.enfermedad_periodontal, obj.enfermedad_periodontal)
        return None
    
    def get_tipo_oclusion_display(self, obj):
        """Descripción de tipo de oclusión"""
        if obj.tipo_oclusion:
            return TIPOS_OCLUSION.get(obj.tipo_oclusion, obj.tipo_oclusion)
        return None
    
    def get_nivel_fluorosis_display(self, obj):
        """Descripción de nivel de fluorosis"""
        if obj.nivel_fluorosis:
            return NIVELES_FLUOROSIS.get(obj.nivel_fluorosis, obj.nivel_fluorosis)
        return None
    
    def get_nivel_gingivitis_display(self, obj):
        """Descripción de nivel de gingivitis"""
        if obj.nivel_gingivitis:
            return obj.get_nivel_gingivitis_display()
        return None
    
    def get_valores_por_pieza(self, obj):
        """Organiza valores por pieza dental con información de alternativas"""
        piezas = ['16', '11', '26', '36', '31', '46']
        resultado = []
        
        # Obtener mapeo de piezas usadas si existe
        piezas_mapeo = {}
        if obj.piezas_usadas_en_registro:
            piezas_mapeo = obj.piezas_usadas_en_registro.get('piezas_mapeo', {})
        
        for pieza in piezas:
            placa = getattr(obj, f'pieza_{pieza}_placa', None)
            calculo = getattr(obj, f'pieza_{pieza}_calculo', None)
            gingivitis = getattr(obj, f'pieza_{pieza}_gingivitis', None)
            
            # Obtener descripciones de escalas
            placa_desc = ESCALA_PLACA.get(placa) if placa is not None else None
            calculo_desc = ESCALA_CALCULO.get(calculo) if calculo is not None else None
            gingivitis_desc = ESCALA_GINGIVITIS.get(gingivitis) if gingivitis is not None else None
            
            # Calcular subtotales
            subtotal_ohi = None
            if placa is not None and calculo is not None:
                subtotal_ohi = placa + calculo
            
            # Obtener información de pieza usada (original o alternativa)
            info_pieza = piezas_mapeo.get(pieza, {})
            pieza_usada = info_pieza.get('codigo_usado', pieza)
            es_alternativa = info_pieza.get('es_alternativa', False)
            
            # Construir mensaje de alternativa si aplica
            mensaje_alternativa = None
            if es_alternativa and pieza_usada != pieza:
                mensaje_alternativa = f"Usando pieza {pieza_usada} como alternativa de {pieza}"
            
            resultado.append({
                'pieza': pieza,
                'pieza_original': pieza,  # Siempre la pieza del índice estándar
                'pieza_usada': pieza_usada,  # La pieza que realmente se evaluó
                'es_alternativa': es_alternativa,
                'mensaje_alternativa': mensaje_alternativa,
                'placa': {
                    'valor': placa,
                    'descripcion': placa_desc,
                    'escala': 'Índice de Placa de Silness & Löe (0-3)'
                },
                'calculo': {
                    'valor': calculo,
                    'descripcion': calculo_desc,
                    'escala': 'Índice de Cálculo de Greene & Vermillion (0-3)'
                },
                'gingivitis': {
                    'valor': gingivitis,
                    'descripcion': gingivitis_desc,
                    'escala': 'Índice Gingival de Löe & Silness (0-3)'
                },
                'subtotal_ohi': subtotal_ohi,
                'completo': all(v is not None for v in [placa, calculo, gingivitis])
            })
        
        return resultado
    def get_informacion_piezas_usadas(self, obj):
        """
        Retorna información estructurada de las piezas usadas
        """
        if not obj.piezas_usadas_en_registro:
            return {}
        
        piezas_estructuradas = []
        mapeo = obj.piezas_usadas_en_registro.get('piezas_mapeo', {})
        
        for pieza_original, info in mapeo.items():
            pieza_usada = info.get('codigo_usado', pieza_original)
            es_alternativa = info.get('es_alternativa', False)
            
            # Obtener valores de los campos del modelo
            datos = {
                'pieza_original': pieza_original,
                'pieza_usada': pieza_usada,
                'es_alternativa': es_alternativa,
                'placa': getattr(obj, f"pieza_{pieza_original}_placa", None),
                'calculo': getattr(obj, f"pieza_{pieza_original}_calculo", None),
                'gingivitis': getattr(obj, f"pieza_{pieza_original}_gingivitis", None),
            }
            
            piezas_estructuradas.append(datos)
        
        return {
            'piezas': piezas_estructuradas,
            'denticion': obj.piezas_usadas_en_registro.get('denticion'),
            'estadisticas': obj.piezas_usadas_en_registro.get('estadisticas')
        }
    def get_calculos_completos(self, obj):
        """
        Obtiene cálculos completos desde informacion_calculo
        Si no existe, calcula en tiempo real
        """
        from api.odontogram.services.indicadores_service import CalculosIndicadoresService
        from api.odontogram.services.indicadores_service import PiezasIndiceService
        
        # Si ya tenemos información de cálculo almacenada, usarla
        if obj.informacion_calculo and 'calculos' in obj.informacion_calculo:
            return obj.informacion_calculo['calculos']
        
        # Si no, calcular en tiempo real
        try:
            # Obtener información de piezas
            info_piezas = PiezasIndiceService.obtener_informacion_piezas(str(obj.paciente_id))
            
            # Recopilar valores
            valores_placa = {}
            valores_calculo = {}
            valores_gingivitis = {}
            
            for pieza_original in info_piezas.get('piezas_mapeo', {}) or info_piezas.get('piezas', {}).keys():
                placa = getattr(obj, f"pieza_{pieza_original}_placa", None)
                calculo = getattr(obj, f"pieza_{pieza_original}_calculo", None)
                gingivitis = getattr(obj, f"pieza_{pieza_original}_gingivitis", None)
                
                if placa is not None:
                    valores_placa[pieza_original] = placa
                if calculo is not None:
                    valores_calculo[pieza_original] = calculo
                if gingivitis is not None:
                    valores_gingivitis[pieza_original] = gingivitis
            
            # Calcular resumen completo
            return CalculosIndicadoresService.calcular_resumen_completo(
                valores_placa, valores_calculo, valores_gingivitis
            )
            
        except Exception as e:
            # En caso de error, retornar estructura básica
            return {
                'error': f"No se pudieron calcular los indicadores: {str(e)}",
                'ohi_s': None,
                'indice_gingival': None,
                'recomendaciones': []
            }
    
    def get_escalas_referencia(self, obj):
        """
        Retorna las escalas de referencia para interpretación
        """
        return {
            'placa': ESCALA_PLACA,
            'calculo': ESCALA_CALCULO,
            'gingivitis': ESCALA_GINGIVITIS,
            'interpretacion_ohi_s': {
                'excelente': '0 - 0.6',
                'bueno': '0.7 - 1.2',
                'regular': '1.3 - 1.8',
                'deficiente': '1.9 - 3.0',
                'pesimo': '> 3.0'
            },
            'interpretacion_gi': {
                'normal': '0 - 0.1',
                'leve': '0.2 - 1.0',
                'moderada': '1.1 - 2.0',
                'severa': '> 2.0'
            }
        }


class IndicadoresSaludBucalCreateSerializer(serializers.ModelSerializer):
    """
    Serializer especializado para creación de indicadores
    con validación completa y manejo de transacciones
    """
    
    class Meta:
        model = IndicadoresSaludBucal
        fields = "__all__"
        read_only_fields = (
            "id", 
            "fecha", 
            "creado_por", 
            "actualizado_por",
            "ohi_promedio_placa", 
            "ohi_promedio_calculo",
            "gi_promedio_gingivitis", 
            "informacion_calculo",
            "piezas_usadas_en_registro"
        )
    
    def validate(self, attrs):
        """
        Validar que al menos 3 piezas tengan datos completos
        """
        piezas = ['16', '11', '26', '36', '31', '46']
        piezas_completas = 0
        piezas_con_datos = []
        
        for pieza in piezas:
            placa = attrs.get(f'pieza_{pieza}_placa')
            calculo = attrs.get(f'pieza_{pieza}_calculo')
            gingivitis = attrs.get(f'pieza_{pieza}_gingivitis')
            
            # Verificar que todos los valores estén presentes
            if all(v is not None for v in [placa, calculo, gingivitis]):
                piezas_completas += 1
                piezas_con_datos.append(pieza)
                
                # Validar rangos (0-3)
                for nombre, valor in [('placa', placa), ('calculo', calculo), ('gingivitis', gingivitis)]:
                    if not (0 <= valor <= 3):
                        raise serializers.ValidationError({
                            f'pieza_{pieza}_{nombre}': f'El valor debe estar entre 0 y 3. Recibido: {valor}'
                        })
        
        if piezas_completas < 3:
            raise serializers.ValidationError({
                'non_field_errors': [
                    f'Se requieren al menos 3 piezas con datos completos (placa, cálculo y gingivitis). '
                    f'Actualmente hay {piezas_completas} piezas completas: {piezas_con_datos}'
                ]
            })
        
        logger.info(f"Validación exitosa: {piezas_completas} piezas con datos completos")
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Override create para usar el servicio modular con manejo de transacciones.
        
        FIX: piezas_usadas_en_registro estaba en read_only_fields, por lo que
        el serializer lo descartaba de validated_data. Ahora se construye
        internamente y se persiste con save() directo tras la creación,
        garantizando que siempre se guarde sin importar qué haga el servicio.
        """
        from api.odontogram.services.indicadores_service import IndicadoresSaludBucalService
        from api.odontogram.services.piezas_service import PiezasIndiceService
        
        # Extraer datos necesarios
        paciente_id = str(validated_data['paciente'].id)
        usuario_id = self.context['request'].user.id
        
        # ===== PASO 1: Construir piezas_usadas_en_registro SIEMPRE =====
        info_piezas = None
        piezas_registro = {}
        
        try:
            info_piezas = PiezasIndiceService.obtener_informacion_piezas(paciente_id)
        except Exception as e:
            logger.warning(
                f"No se pudo obtener info de piezas para {paciente_id}: {str(e)}. "
                f"Se creará el registro sin trazabilidad de piezas."
            )
        
        if info_piezas:
            piezas_mapeo = info_piezas.get('piezas_mapeo') or info_piezas.get('piezas', {})
            
            mapeo_piezas_usadas = {}
            for pieza_original, info in piezas_mapeo.items():
                pieza_usada = info.get('codigo_usado', pieza_original)
                
                tiene_datos = False
                datos_pieza = {}
                
                for campo in ['placa', 'calculo', 'gingivitis']:
                    campo_entrada = f"pieza_{pieza_original}_{campo}"
                    if campo_entrada in validated_data and validated_data[campo_entrada] is not None:
                        tiene_datos = True
                        datos_pieza[campo] = validated_data[campo_entrada]
                
                if tiene_datos:
                    mapeo_piezas_usadas[pieza_original] = {
                        'codigo_usado': pieza_usada,
                        'es_alternativa': info.get('es_alternativa', pieza_usada != pieza_original),
                        'codigo_original': pieza_original,
                        'disponible': info.get('disponible', True),
                        'diente_id': info.get('diente_id'),
                        'ambos_ausentes': info.get('ambos_ausentes', False),
                        'datos': datos_pieza
                    }
            
            piezas_registro = {
                'piezas_mapeo': mapeo_piezas_usadas,
                'denticion': info_piezas.get('denticion'),
                'estadisticas': info_piezas.get('estadisticas'),
                'fecha_registro': str(timezone.now())
            }
        # ===== FIN PASO 1 =====
        
        try:
            # PASO 2: Intentar crear con el servicio modular
            datos_para_servicio = validated_data.copy()
            datos_para_servicio['piezas_usadas_en_registro'] = piezas_registro
            
            indicadores = IndicadoresSaludBucalService.crear_indicadores_completos(
                paciente_id=paciente_id,
                usuario_id=usuario_id,
                datos=datos_para_servicio
            )
            
            # PASO 3: Garantizar persistencia de piezas_usadas_en_registro
            # El servicio puede no haber guardado este campo, así que lo forzamos.
            if not indicadores.piezas_usadas_en_registro and piezas_registro:
                indicadores.piezas_usadas_en_registro = piezas_registro
                indicadores.save(update_fields=['piezas_usadas_en_registro'])
            
            logger.info(
                f"Indicadores creados exitosamente para paciente {paciente_id} "
                f"(ID: {indicadores.id})"
            )
            return indicadores
            
        except serializers.ValidationError:
            raise
            
        except Exception as e:
            logger.error(
                f"Error en create de indicadores para paciente {paciente_id}: {str(e)}",
                exc_info=True
            )
            
            # Fallback: crear registro básico INCLUYENDO piezas_usadas_en_registro
            try:
                validated_data['creado_por_id'] = usuario_id
                indicadores = super().create(validated_data)
                
                # Persistir piezas_usadas_en_registro que el serializer descartó
                if piezas_registro:
                    indicadores.piezas_usadas_en_registro = piezas_registro
                    indicadores.save(update_fields=['piezas_usadas_en_registro'])
                
                # Calcular promedios básicos
                from api.odontogram.services.indicadores_service import (
                    IndicadoresSaludBucalService as Service
                )
                Service.calcular_y_guardar_promedios(indicadores)
                
                logger.warning(
                    f"Se creó registro básico de indicadores (fallback) "
                    f"para paciente {paciente_id}"
                )
                return indicadores
                
            except Exception as fallback_error:
                logger.error(
                    f"Error en fallback de creación: {str(fallback_error)}",
                    exc_info=True
                )
                raise serializers.ValidationError(
                    f"Error al crear indicadores: {str(e)}"
                )


class IndicadoresSaludBucalUpdateSerializer(IndicadoresSaludBucalSerializer):
    """
    Serializer especializado para actualización de indicadores
    """
    
    class Meta(IndicadoresSaludBucalSerializer.Meta):
        fields = "__all__"
        read_only_fields = (
            "id", 
            "fecha", 
            "creado_por", 
            "actualizado_por",
            "ohi_promedio_placa", 
            "ohi_promedio_calculo",
            "gi_promedio_gingivitis", 
            "informacion_calculo"
        )
    
    def update(self, instance, validated_data):
        """
        Override update para usar el servicio modular
        """
        from api.odontogram.services.indicadores_service import IndicadoresSaludBucalService
        
        # Si no hay campos de pieza dental en los datos, actualizar normal
        campos_pieza = any(field.startswith('pieza_') for field in validated_data.keys())
        
        if not campos_pieza:
            # Actualización simple de campos básicos
            validated_data['actualizado_por'] = self.context['request'].user
            return super().update(instance, validated_data)
        
        # Actualización completa con servicio modular
        try:
            usuario_id = self.context['request'].user.id
            
            indicadores = IndicadoresSaludBucalService.actualizar_indicadores(
                indicadores_id=str(instance.id),
                usuario_id=usuario_id,
                datos=validated_data
            )
            return indicadores
            
        except Exception as e:
            # Si falla el servicio modular, actualizar básico
            validated_data['actualizado_por'] = self.context['request'].user
            indicadores = super().update(instance, validated_data)
            
            # Recalcular promedios
            from api.odontogram.services.indicadores_service import IndicadoresSaludBucalService as Service
            Service.calcular_y_guardar_promedios(indicadores)
            
            return indicadores