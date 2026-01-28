"""
Punto de unión - Exporta todos los serializers
Este archivo centraliza las importaciones para mantener compatibilidad
con el código existente y facilitar el uso de los serializers.
"""

# Serializers base y utilidades
from .base import (
    SafeDateField,
    BaseWritableNestedSerializer,
    DateFormatterMixin,
)

# Datos de paciente
from .patient_data import PatientInfoMixin

# Antecedentes médicos
from .medical_history import (
    WritableAntecedentesPersonalesSerializer,
    WritableAntecedentesFamiliaresSerializer,
)

# Constantes vitales
from .vital_signs import (
    WritableConstantesVitalesSerializer,
    VitalSignsFieldsMixin,
)

# Examen estomatognático
from .stomatognathic_exam import WritableExamenEstomatognaticoSerializer

# Serializers principales de ClinicalRecord
from .clinical_record import (
    ClinicalRecordSerializer,
    ClinicalRecordDetailSerializer,
    ClinicalRecordCreateSerializer,
    ClinicalRecordCloseSerializer,
    ClinicalRecordReopenSerializer,
)

# Exportar todo para compatibilidad con imports existentes
__all__ = [
    # Base
    'SafeDateField',
    'BaseWritableNestedSerializer',
    'DateFormatterMixin',
    
    # Patient Data
    'PatientInfoMixin',
    
    # Medical History
    'WritableAntecedentesPersonalesSerializer',
    'WritableAntecedentesFamiliaresSerializer',
    
    # Vital Signs
    'WritableConstantesVitalesSerializer',
    'VitalSignsFieldsMixin',
    
    # Stomatognathic Exam
    'WritableExamenEstomatognaticoSerializer',
    
    # Clinical Record
    'ClinicalRecordSerializer',
    'ClinicalRecordDetailSerializer',
    'ClinicalRecordCreateSerializer',
    'ClinicalRecordCloseSerializer',
    'ClinicalRecordReopenSerializer',
    
    #odontograma
    
    
]
