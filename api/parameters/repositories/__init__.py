# api/parameters/repositories/__init__.py
# Exportar repositorios
from .horario_repository import HorarioRepository
from .parametro_repository import ParametroRepository

__all__ = ['HorarioRepository', 'ParametroRepository']