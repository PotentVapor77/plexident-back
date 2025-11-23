# odontogram/factories.py
"""
Factory Pattern - Creación de objetos complejos de forma centralizada
Facilita la creación de instancias con configuraciones predefinidas
"""
from typing import Dict, List, Any, Optional
from api.odontogram.models import (
    CategoriaDiagnostico,
    Diagnostico,
    AreaAfectada,
    TipoAtributoClinico,
    OpcionAtributoClinico,
)


class DiagnosticoFactory:
    """
    Factory para crear diagnósticos con configuraciones predefinidas
    """

    # Plantillas de diagnósticos comunes
    PLANTILLAS = {
        'caries_simple': {
            'simbolo_color': 'PATOLOGIA',
            'areas': ['corona'],
            'atributos': ['erupcion'],
        },
        'fractura': {
            'simbolo_color': 'PATOLOGIA',
            'atributos': ['estado_procedimiento'],
        },
        'restauracion': {
            'simbolo_color': 'REALIZADO',
            'areas': ['corona'],
            'atributos': ['material_restauracion', 'estado_restauracion'],
        },
        'restauracion_compleja': {
            'simbolo_color': 'REALIZADO',
            'areas': ['corona', 'raiz'],
            'atributos': ['material_restauracion', 'estado_restauracion', 'estado_procedimiento'],
        },
        'endodoncia': {
            'simbolo_color': 'ENDODONCIA',
            'areas': ['corona', 'raiz'],
            'atributos': ['estado_procedimiento'],
        },
        'anomalia': {
            'simbolo_color': 'ANOMALIA',
            'areas': ['general'],
            'atributos': ['erupcion'],
        },
    }

    @classmethod
    def crear_desde_plantilla(
        cls,
        plantilla: str,
        categoria: CategoriaDiagnostico,
        key: str,
        nombre: str,
        siglas: str,
        prioridad: int,
        **kwargs
    ) -> Diagnostico:
        """
        Crea un diagnóstico basado en una plantilla predefinida
        """
        if plantilla not in cls.PLANTILLAS:
            raise ValueError(f"Plantilla '{plantilla}' no existe")

        config = cls.PLANTILLAS[plantilla].copy()
        config.update(kwargs)  # Permite sobrescribir valores

        # Crear el diagnóstico
        diagnostico = Diagnostico.objects.create(
            categoria=categoria,
            key=key,
            nombre=nombre,
            siglas=siglas,
            prioridad=prioridad,
            simbolo_color=config.get('simbolo_color', 'PATOLOGIA'),
            activo=True
        )

        return diagnostico

    @classmethod
    def crear_caries(
        cls,
        categoria: CategoriaDiagnostico,
        nivel_icdas: int,
        **kwargs
    ) -> Diagnostico:
        """
        Factory específico para crear diagnósticos de caries
        """
        # Mapeo de prioridad según nivel ICDAS
        prioridades = {
            1: 2,  # ICDAS 1: Baja prioridad
            2: 3,  # ICDAS 2: Media prioridad
            3: 4,  # ICDAS 3: Alta prioridad
            4: 5,  # ICDAS 4: Crítica
            5: 5,  # ICDAS 5: Crítica
            6: 5,  # ICDAS 6: Crítica
        }

        return cls.crear_desde_plantilla(
            plantilla='caries_simple',
            categoria=categoria,
            key=f'caries_icdas_{nivel_icdas}',
            nombre=f'Caries ICDAS {nivel_icdas}',
            siglas=f'C{nivel_icdas}',
            prioridad=prioridades.get(nivel_icdas, 3),
            **kwargs
        )

    @classmethod
    def crear_restauracion(
        cls,
        categoria: CategoriaDiagnostico,
        tipo: str,  # 'simple', 'compleja', 'provisional', 'definitiva'
        **kwargs
    ) -> Diagnostico:
        """
        Factory específico para restauraciones
        """
        configs = {
            'simple': {
                'key': 'restauracion_simple',
                'nombre': 'Restauración Simple',
                'siglas': 'RestS',
                'prioridad': 2,
                'plantilla': 'restauracion',
            },
            'compleja': {
                'key': 'restauracion_compleja',
                'nombre': 'Restauración Compleja',
                'siglas': 'RestC',
                'prioridad': 3,
                'plantilla': 'restauracion_compleja',
            },
            'provisional': {
                'key': 'corona_provisional',
                'nombre': 'Corona Provisional',
                'siglas': 'CorP',
                'prioridad': 2,
                'plantilla': 'restauracion_compleja',
            },
            'definitiva': {
                'key': 'corona_definitiva',
                'nombre': 'Corona Definitiva',
                'siglas': 'CorD',
                'prioridad': 2,
                'plantilla': 'restauracion_compleja',
            },
        }

        config = configs.get(tipo)
        if not config:
            raise ValueError(f"Tipo de restauración '{tipo}' no válido")

        plantilla = config.pop('plantilla')
        config.update(kwargs)

        return cls.crear_desde_plantilla(
            plantilla=plantilla,
            categoria=categoria,
            **config
        )


class AtributoClinicoFactory:
    """
    Factory para crear tipos de atributos con sus opciones
    """

    # Plantillas de atributos predefinidos
    PLANTILLAS = {
        'estado_binario': {
            'opciones': [
                {'key': 'si', 'nombre': 'Sí', 'prioridad': 5, 'orden': 1},
                {'key': 'no', 'nombre': 'No', 'prioridad': 1, 'orden': 2},
            ]
        },
        'estado_calidad': {
            'opciones': [
                {'key': 'excelente', 'nombre': 'Excelente', 'prioridad': 1, 'orden': 1},
                {'key': 'buena', 'nombre': 'Buena', 'prioridad': 2, 'orden': 2},
                {'key': 'regular', 'nombre': 'Regular', 'prioridad': 3, 'orden': 3},
                {'key': 'mala', 'nombre': 'Mala', 'prioridad': 4, 'orden': 4},
                {'key': 'critica', 'nombre': 'Crítica', 'prioridad': 5, 'orden': 5},
            ]
        },
        'nivel_severidad': {
            'opciones': [
                {'key': 'ninguno', 'nombre': 'Ninguno', 'prioridad': 1, 'orden': 1},
                {'key': 'leve', 'nombre': 'Leve', 'prioridad': 2, 'orden': 2},
                {'key': 'moderado', 'nombre': 'Moderado', 'prioridad': 3, 'orden': 3},
                {'key': 'severo', 'nombre': 'Severo', 'prioridad': 5, 'orden': 4},
            ]
        },
        'grados_movilidad': {
            'opciones': [
                {'key': 'grado_0', 'nombre': 'Grado 0', 'prioridad': 1, 'orden': 1},
                {'key': 'grado_1', 'nombre': 'Grado 1', 'prioridad': 2, 'orden': 2},
                {'key': 'grado_2', 'nombre': 'Grado 2', 'prioridad': 4, 'orden': 3},
                {'key': 'grado_3', 'nombre': 'Grado 3', 'prioridad': 5, 'orden': 4},
            ]
        },
    }

    @classmethod
    def crear_desde_plantilla(
        cls,
        plantilla: str,
        key: str,
        nombre: str,
        descripcion: str = "",
        opciones_extra: Optional[List[Dict]] = None
    ) -> TipoAtributoClinico:
        """
        Crea un tipo de atributo con opciones predefinidas
        """
        if plantilla not in cls.PLANTILLAS:
            raise ValueError(f"Plantilla '{plantilla}' no existe")

        # Crear tipo de atributo
        tipo = TipoAtributoClinico.objects.create(
            key=key,
            nombre=nombre,
            descripcion=descripcion,
            activo=True
        )

        # Crear opciones de la plantilla
        opciones = cls.PLANTILLAS[plantilla]['opciones'].copy()

        # Agregar opciones extra si existen
        if opciones_extra:
            opciones.extend(opciones_extra)

        for opcion_data in opciones:
            OpcionAtributoClinico.objects.create(
                tipo_atributo=tipo,
                **opcion_data,
                activo=True
            )

        return tipo

    @classmethod
    def crear_material(
        cls,
        key: str,
        nombre: str,
        materiales: List[str]
    ) -> TipoAtributoClinico:
        """
        Factory específico para crear atributos de tipo material
        Los materiales no tienen prioridad (son descriptivos)
        """
        tipo = TipoAtributoClinico.objects.create(
            key=key,
            nombre=nombre,
            descripcion=f"Material utilizado en {nombre.lower()}",
            activo=True
        )

        for i, material in enumerate(materiales):
            OpcionAtributoClinico.objects.create(
                tipo_atributo=tipo,
                key=material.lower().replace(' ', '_'),
                nombre=material,
                prioridad=None,  # Los materiales no tienen prioridad
                orden=i + 1,
                activo=True
            )

        return tipo

    @classmethod
    def crear_estado_procedimiento(
        cls,
        key: str,
        nombre: str
    ) -> TipoAtributoClinico:
        """
        Factory específico para estados de procedimiento
        """
        tipo = TipoAtributoClinico.objects.create(
            key=key,
            nombre=nombre,
            descripcion="Estado del procedimiento dental",
            activo=True
        )

        estados = [
            {'key': 'planificado', 'nombre': 'Planificado', 'orden': 1},
            {'key': 'en_proceso', 'nombre': 'En Proceso', 'orden': 2},
            {'key': 'finalizado', 'nombre': 'Finalizado', 'orden': 3},
            {'key': 'cancelado', 'nombre': 'Cancelado', 'orden': 4},
        ]

        for estado in estados:
            OpcionAtributoClinico.objects.create(
                tipo_atributo=tipo,
                prioridad=None,  # Estados de procedimiento no tienen prioridad clínica
                activo=True,
                **estado
            )

        return tipo


class CategoriaDiagnosticoFactory:
    """
    Factory para crear categorías de diagnóstico
    """

    # Colores estándar por tipo de categoría
    COLORES_ESTANDAR = {
        'patologia': 'PATOLOGIA',
        'tratamiento': 'REALIZADO',
        'endodoncia': 'ENDODONCIA',
        'ausencia': 'AUSENCIA',
        'anomalia': 'ANOMALIA',
    }

    # Prioridades estándar por tipo
    PRIORIDADES_ESTANDAR = {
        'patologia': 'ALTA',
        'tratamiento': 'MEDIA',
        'endodoncia': 'MEDIA',
        'ausencia': 'INFORMATIVA',
        'anomalia': 'ESTRUCTURAL',
    }

    @classmethod
    def crear(
        cls,
        key: str,
        nombre: str,
        tipo: str = 'patologia',
        color_key: Optional[str] = None,
        prioridad_key: Optional[str] = None
    ) -> CategoriaDiagnostico:
        """
        Crea una categoría con configuración estándar
        """
        return CategoriaDiagnostico.objects.create(
            key=key,
            nombre=nombre,
            color_key=color_key or cls.COLORES_ESTANDAR.get(tipo, 'PATOLOGIA'),
            prioridad_key=prioridad_key or cls.PRIORIDADES_ESTANDAR.get(tipo, 'MEDIA'),
            activo=True
        )


class ConfiguracionInicialFactory:
    """
    Factory para crear configuraciones iniciales completas
    """

    @classmethod
    def crear_configuracion_basica(cls):
        """
        Crea una configuración básica de odontograma desde cero
        """
        # Crear categorías
        cat_patologia = CategoriaDiagnosticoFactory.crear(
            key='patologia_activa',
            nombre='Patología Activa',
            tipo='patologia'
        )

        cat_restauracion = CategoriaDiagnosticoFactory.crear(
            key='restauracion',
            nombre='Restauración',
            tipo='tratamiento'
        )

        # Crear diagnósticos de caries
        for nivel in range(1, 7):
            DiagnosticoFactory.crear_caries(
                categoria=cat_patologia,
                nivel_icdas=nivel
            )

        # Crear restauraciones
        for tipo in ['simple', 'compleja', 'provisional', 'definitiva']:
            DiagnosticoFactory.crear_restauracion(
                categoria=cat_restauracion,
                tipo=tipo
            )

        # Crear atributos clínicos
        AtributoClinicoFactory.crear_material(
            key='material_restauracion',
            nombre='Material de Restauración',
            materiales=['Amalgama', 'Resina', 'Porcelana', 'Oro', 'Ionómero']
        )

        AtributoClinicoFactory.crear_desde_plantilla(
            plantilla='estado_calidad',
            key='estado_restauracion',
            nombre='Estado de Restauración',
            descripcion='Condición actual de la restauración'
        )

        return {
            'categorias_creadas': 2,
            'diagnosticos_creados': Diagnostico.objects.count(),
            'atributos_creados': TipoAtributoClinico.objects.count(),
        }
