# odontogram/serializers.py

"""Serializadores para la API REST del sistema de odontogramas extensible."""

from rest_framework import serializers
from .models import (CategoriaDiagnostico, Diagnostico, AreaAfectada, DiagnosticoAreaAfectada ,TipoAtributoClinico, OpcionAtributoClinico ,DiagnosticoAtributoClinico,
)

# Serializadores basicos

class AreaAfectadaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaAfectada
        fields = ['id', 'key', 'nombre', 'activo']


class OpcionAtributoClinicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcionAtributoClinico
        fields = [
            'id', 'key', 'nombre', 'prioridad', 
            'orden', 'activo'
        ]


class TipoAtributoClinicoSerializer(serializers.ModelSerializer):
    opciones = OpcionAtributoClinicoSerializer(many=True, read_only=True)

    class Meta:
        model = TipoAtributoClinico
        fields = [
            'id', 'key', 'nombre', 'descripcion', 
            'opciones', 'activo'
        ]

# Serializadores anidados por diagnostico
class DiagnosticoListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados"""
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = Diagnostico
        fields = [
            'id', 'key', 'nombre', 'siglas', 
            'categoria', 'categoria_nombre', 
            'simbolo_color', 'prioridad', 'activo'
        ]


class DiagnosticoDetailSerializer(serializers.ModelSerializer):
    """Serializer completo con áreas y atributos"""
    categoria = serializers.CharField(source='categoria.nombre', read_only=True)
    categoria_id = serializers.IntegerField(source='categoria.id', read_only=True)
    areas_afectadas = serializers.SerializerMethodField()
    atributos_clinicos = serializers.SerializerMethodField()

    class Meta:
        model = Diagnostico
        fields = [
            'id', 'key', 'nombre', 'siglas',
            'categoria', 'categoria_id',
            'simbolo_color', 'prioridad',
            'areas_afectadas',
            'atributos_clinicos',
            'activo'
        ]

    def get_areas_afectadas(self, obj):
        """Obtiene las áreas afectadas relacionadas"""
        relaciones = DiagnosticoAreaAfectada.objects.filter(
            diagnostico=obj
        ).select_related('area')
        return [
            {'key': rel.area.key, 'nombre': rel.area.nombre}
            for rel in relaciones
        ]

    def get_atributos_clinicos(self, obj):
        """Obtiene los atributos clínicos aplicables con sus opciones"""
        relaciones = DiagnosticoAtributoClinico.objects.filter(
            diagnostico=obj
        ).select_related('tipo_atributo')

        resultado = {}
        for rel in relaciones:
            tipo = rel.tipo_atributo
            opciones = OpcionAtributoClinico.objects.filter(
                tipo_atributo=tipo,
                activo=True
            ).order_by('orden', 'nombre')

            resultado[tipo.key] = [
                {
                    'key': opcion.key,
                    'nombre': opcion.nombre,
                    'prioridad': opcion.prioridad,
                }
                for opcion in opciones
            ]

        return resultado


class CategoriaDiagnosticoSerializer(serializers.ModelSerializer):
    diagnosticos = DiagnosticoListSerializer(many=True, read_only=True)

    class Meta:
        model = CategoriaDiagnostico
        fields = [
            'id', 'key', 'nombre', 
            'color_key', 'prioridad_key',
            'diagnosticos', 'activo'
        ]

# Serializadores completos
class OdontogramaConfigSerializer(serializers.Serializer):
    """
    Serializer que retorna toda la configuración del odontograma
    para consumo del frontend
    """
    categorias = CategoriaDiagnosticoSerializer(many=True)
    areas_afectadas = AreaAfectadaSerializer(many=True)
    tipos_atributos = TipoAtributoClinicoSerializer(many=True)
