# odontogram/repositories/repositories_odontogram.py
"""
Repository Pattern: Abstrae la lógica de acceso a datos
Proporciona una interfaz consistente para operaciones CRUD
"""

from typing import List, Optional, Dict, Any
from django.db.models import QuerySet, Prefetch
from api.odontogram.models import (
    CategoriaDiagnostico,
    Diagnostico,
    AreaAfectada,
    TipoAtributoClinico,
    OpcionAtributoClinico,
    DiagnosticoAreaAfectada,
    DiagnosticoAtributoClinico,
)


class BaseRepository:
    """Repositorio base con operaciones comunes"""

    model = None

    def get_by_id(self, id: int) -> Optional[Any]:
        """Obtiene un registro por ID"""
        try:
            return self.model.objects.get(id=id, activo=True)
        except self.model.DoesNotExist:
            return None

    def get_all(self) -> QuerySet:
        """Obtiene todos los registros activos"""
        return self.model.objects.filter(activo=True)

    def create(self, **kwargs) -> Any:
        """Crea un nuevo registro"""
        return self.model.objects.create(**kwargs)

    def update(self, id: int, **kwargs) -> Optional[Any]:
        """Actualiza un registro existente"""
        instance = self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            instance.save()
        return instance

    def soft_delete(self, id: int) -> bool:
        """Desactiva un registro (soft delete)"""
        instance = self.get_by_id(id)
        if instance:
            instance.activo = False
            instance.save()
            return True
        return False


class CategoriaDiagnosticoRepository(BaseRepository):
    """Repositorio para Categorías de Diagnóstico"""

    model = CategoriaDiagnostico

    def get_with_diagnosticos(self) -> QuerySet:
        """Obtiene categorías con sus diagnósticos"""
        return self.get_all().prefetch_related(
            Prefetch(
                'diagnosticos',
                queryset=Diagnostico.objects.filter(activo=True)
            )
        )

    def get_by_key(self, key: str) -> Optional[CategoriaDiagnostico]:
        """Obtiene una categoría por su key"""
        try:
            return self.model.objects.get(key=key, activo=True)
        except self.model.DoesNotExist:
            return None

    def get_by_prioridad(self, prioridad_key: str) -> QuerySet:
        """Filtra categorías por nivel de prioridad"""
        return self.get_all().filter(prioridad_key=prioridad_key)


class DiagnosticoRepository(BaseRepository):
    """Repositorio para Diagnósticos"""

    model = Diagnostico

    def get_with_relations(self, id: int) -> Optional[Diagnostico]:
        """Obtiene un diagnóstico con todas sus relaciones"""
        try:
            return self.model.objects.select_related('categoria').prefetch_related(
                'areas_relacionadas__area',
                'atributos_aplicables__tipo_atributo__opciones'
            ).get(id=id, activo=True)
        except self.model.DoesNotExist:
            return None

    def get_by_categoria(self, categoria_id: int) -> QuerySet:
        """Filtra diagnósticos por categoría"""
        return self.get_all().filter(categoria_id=categoria_id)

    def get_by_prioridad(self, prioridad: int) -> QuerySet:
        """Filtra diagnósticos por nivel de prioridad"""
        return self.get_all().filter(prioridad=prioridad)

    def get_by_prioridad_range(self, min_prioridad: int, max_prioridad: int) -> QuerySet:
        """Filtra diagnósticos por rango de prioridad"""
        return self.get_all().filter(
            prioridad__gte=min_prioridad,
            prioridad__lte=max_prioridad
        )

    def get_criticos(self) -> QuerySet:
        """Obtiene diagnósticos críticos (prioridad 4-5)"""
        return self.get_by_prioridad_range(4, 5)

    def search(self, query: str) -> QuerySet:
        """Busca diagnósticos por nombre o siglas"""
        return self.get_all().filter(
            nombre__icontains=query
        ) | self.get_all().filter(
            siglas__icontains=query
        )


class AreaAfectadaRepository(BaseRepository):
    """Repositorio para Áreas Afectadas"""

    model = AreaAfectada

    def get_by_diagnostico(self, diagnostico_id: int) -> QuerySet:
        """Obtiene áreas relacionadas a un diagnóstico"""
        relaciones = DiagnosticoAreaAfectada.objects.filter(
            diagnostico_id=diagnostico_id
        ).values_list('area_id', flat=True)
        return self.get_all().filter(id__in=relaciones)


class TipoAtributoClinicoRepository(BaseRepository):
    """Repositorio para Tipos de Atributos Clínicos"""

    model = TipoAtributoClinico

    def get_with_opciones(self) -> QuerySet:
        """Obtiene tipos de atributos con sus opciones"""
        return self.get_all().prefetch_related(
            Prefetch(
                'opciones',
                queryset=OpcionAtributoClinico.objects.filter(activo=True).order_by('orden')
            )
        )

    def get_by_diagnostico(self, diagnostico_id: int) -> QuerySet:
        """Obtiene atributos aplicables a un diagnóstico"""
        relaciones = DiagnosticoAtributoClinico.objects.filter(
            diagnostico_id=diagnostico_id
        ).values_list('tipo_atributo_id', flat=True)
        return self.get_all().filter(id__in=relaciones)


class OpcionAtributoClinicoRepository(BaseRepository):
    """Repositorio para Opciones de Atributos Clínicos"""

    model = OpcionAtributoClinico

    def get_by_tipo(self, tipo_atributo_id: int) -> QuerySet:
        """Obtiene opciones de un tipo específico"""
        return self.get_all().filter(tipo_atributo_id=tipo_atributo_id).order_by('orden')

    def get_con_prioridad(self, tipo_atributo_id: int) -> QuerySet:
        """Obtiene opciones que tienen prioridad definida"""
        return self.get_by_tipo(tipo_atributo_id).exclude(prioridad__isnull=True)

    def get_sin_prioridad(self, tipo_atributo_id: int) -> QuerySet:
        """Obtiene opciones sin prioridad (descriptivas)"""
        return self.get_by_tipo(tipo_atributo_id).filter(prioridad__isnull=True)