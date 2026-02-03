# patients/models/__init__.py
from .base import BaseModel
from .constants import *
from .paciente import Paciente
from .antecedentes_personales import AntecedentesPersonales
from .antecedentes_familiares import AntecedentesFamiliares
from .constantes_vitales import ConstantesVitales
from .examen_estomatognatico import ExamenEstomatognatico
from .examenes_complementarios import ExamenesComplementarios

__all__ = [
    'BaseModel',
    'Paciente',
    'AntecedentesPersonales',
    'AntecedentesFamiliares',
    'ConstantesVitales',
    'ExamenEstomatognatico',
    'ExamenesComplementarios'
]