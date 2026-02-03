# api/odontogram/serializers.py

from api.odontogram.models import Diagnostico, DiagnosticoAtributoClinico
import serializers


class DiagnosticoSerializer(serializers.ModelSerializer):
    """Serializer para diagnósticos del odontograma"""
    
    atributos_clinicos = serializers.SerializerMethodField()
    
    class Meta:
        model = Diagnostico
        fields = [
            'id',
            'key',
            'categoria',
            'nombre',
            'siglas',
            'simbolo_color',
            'simbolo_formulario_033',
            'superficie_aplicables',
            'atributos_clinicos',  
            
        ]
    
    def get_atributos_clinicos(self, obj):
        """Obtiene tipos de atributos con sus opciones"""
        relaciones = DiagnosticoAtributoClinico.objects.filter(
            diagnostico=obj
        ).select_related('tipo_atributo').prefetch_related(
            'tipo_atributo__opciones'
        )
        
        return [
            {
                'key': rel.tipo_atributo.key,
                'nombre': rel.tipo_atributo.nombre,
                'descripcion': rel.tipo_atributo.descripcion,
                'opciones': [
                    {
                        'key': opcion.key,
                        'nombre': opcion.nombre,
                        'orden': opcion.orden,
                        'prioridad': opcion.prioridad,
                    }
                    for opcion in rel.tipo_atributo.opciones.filter(
                        activo=True
                    ).order_by('orden')
                ]
            }
            for rel in relaciones
        ]
