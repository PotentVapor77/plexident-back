# api/odontogram/services/__init__.py
from .indicadores_service import IndicadoresSaludBucalService
from .piezas_service import PiezasIndiceService
from .calculos_service import CalculosIndicadoresService
from .odontogram_services import OdontogramaService, IndiceCariesService

__all__ = [
    'IndicadoresSaludBucalService',
    'PiezasIndiceService',
    'CalculosIndicadoresService',
    'OdontogramaService',
    'IndiceCariesService',
]