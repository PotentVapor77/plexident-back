"""
Punto de unión - Exporta todos los ViewSets
Este archivo centraliza las importaciones para facilitar el uso
y mantener compatibilidad con el código existente.
"""

# Utilidades y mixins base
from .base import (
    ClinicalRecordPagination,
    BasePermissionMixin,
    QuerysetOptimizationMixin,
    SearchFilterMixin,
    ActiveFilterMixin,
    LoggingMixin,
)

# ViewSet principal
from .clinical_record_viewset import ClinicalRecordViewSet

# ViewSets futuros (cuando estén implementados)
# from .odontogram_viewset import OdontogramViewSet
# from .oral_health_viewset import OralHealthIndicatorsViewSet
# from .diagnostic_viewset import DiagnosticViewSet
# from .treatment_viewset import TreatmentPlanViewSet
# from .complementary_exams_viewset import ComplementaryExamViewSet

__all__ = [
    # Base
    'ClinicalRecordPagination',
    'BasePermissionMixin',
    'QuerysetOptimizationMixin',
    'SearchFilterMixin',
    'ActiveFilterMixin',
    'LoggingMixin',
    
    # ViewSets
    'ClinicalRecordViewSet',
    
    # Futuros (descomentar cuando se implementen)
    # 'OdontogramViewSet',
    # 'OralHealthIndicatorsViewSet',
    # 'DiagnosticViewSet',
    # 'TreatmentPlanViewSet',
    # 'ComplementaryExamViewSet',
]
