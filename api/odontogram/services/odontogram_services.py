# odontogram/services/odontogram_services.py
"""
Servicios para la nueva estructura de Odontograma
Maneja: Paciente -> Diente -> Superficie -> DiagnosticoDental
"""

from collections import defaultdict
from typing import List, Dict, Any, Optional
from venv import logger
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from api.odontogram.models import (
    IndicadoresSaludBucal,
    IndiceCariesSnapshot,
    Paciente,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    Diagnostico,
)
from api.odontogram.services.indicadores_service import IndicadoresSaludBucalService as NuevoIndicadoresService
from api.odontogram.services.odontogramaDiagnostico_service import OdontogramaDiagnosticoService
from api.odontogram.services.odontogramaEstadoDiente_service import OdontogramaEstadoDienteService
from api.odontogram.services.odontogramaRead_service import OdontogramaReadService
from api.odontogram.services.odontogramaWrite_service import OdontogramaWriteService
from api.odontogram.constants import FDIConstants

User = get_user_model()

CARIES_KEYS = {"caries"}
OBTURADO_KEYS = {
    "obturacion",
    "sellante_realizado",
    "corona_realizada",
    "protesis_fija_realizada",
    "protesis_removible_realizada",
}
AUSENTE_KEYS = {"ausente"}

class OdontogramaService:

        def __init__(self) -> None:
            self._write = OdontogramaWriteService()
            self._read = OdontogramaReadService()
            self._diente = OdontogramaEstadoDienteService()
            self._diag = OdontogramaDiagnosticoService()

        @transaction.atomic
        def guardar_odontograma_completo(
            self,
            paciente_id: str,
            odontologo_id: int,
            odontograma_data: Dict[str, Dict[str, List[Dict[str, Any]]]],
        ) -> Dict[str, Any]:
            
            resultado = self._write.guardar_odontograma_completo(
                paciente_id=paciente_id,
                odontologo_id=odontologo_id,
                odontograma_data=odontograma_data,
            )
        
            return resultado

        def obtener_odontograma_completo(self, paciente_id: str) -> Dict[str, Any]:
            return self._read.obtener_odontograma_completo(paciente_id=paciente_id)

        @transaction.atomic
        def marcar_diente_ausente(
            self, paciente_id: str, codigo_fdi: str, odontologo_id: int
        ) -> Diente:
            return self._diente.marcar_diente_ausente(
                paciente_id=paciente_id,
                codigo_fdi=codigo_fdi,
                odontologo_id=odontologo_id,
            )

        @transaction.atomic
        def marcar_diagnostico_tratado(
            self, diagnostico_id: str, odontologo_id: int
        ) -> DiagnosticoDental:
            return self._diag.marcar_diagnostico_tratado(
                diagnostico_id=diagnostico_id,
                odontologo_id=odontologo_id,
            )

        @transaction.atomic
        def eliminar_diagnostico(self, diagnostico_id: str, odontologo_id: int) -> bool:
            return self._diag.eliminar_diagnostico(
                diagnostico_id=diagnostico_id,
                odontologo_id=odontologo_id,
            )

        @transaction.atomic
        def eliminardiagnosticosbatch(
            self, diagnosticoids: List[str], odontologoid: int
        ) -> Dict[str, Any]:
            # mantiene exactamente la firma esperada por las views
            return self._diag.eliminar_diagnosticos_batch(
                diagnostico_ids=diagnosticoids,
                odontologo_id=odontologoid,
            )

        @transaction.atomic
        def actualizar_diagnostico(
            self,
            diagnostico_id: str,
            descripcion: Optional[str] = None,
            atributos_clinicos: Optional[Dict] = None,
            estado_tratamiento: Optional[str] = None,
            prioridad_asignada: Optional[int] = None,
            fecha_tratamiento: Optional[str] = None,
            diagnostico_catalogo_id: Optional[int] = None,
            odontologo_id: Optional[int] = None,
        ) -> Optional[DiagnosticoDental]:
            return self._diag.actualizar_diagnostico(
                diagnostico_id=diagnostico_id,
                descripcion=descripcion,
                atributos_clinicos=atributos_clinicos,
                estado_tratamiento=estado_tratamiento,
                prioridad_asignada=prioridad_asignada,
                fecha_tratamiento=fecha_tratamiento,
                diagnostico_catalogo_id=diagnostico_catalogo_id,
                odontologo_id=odontologo_id,
            )

        def obtener_diagnosticos_paciente(
            self, paciente_id: str, estado_tratamiento: Optional[str] = None
        ) -> List[DiagnosticoDental]:
            return self._read.obtener_diagnosticos_paciente(
                paciente_id=paciente_id,
                estado_tratamiento=estado_tratamiento,
            )
            
        def aplicar_diagnostico_desde_frontend(
            diente, superficie_id_frontend, diagnostico_key, **kwargs
        ):
            nombre_superficie = SuperficieDental.normalizar_superficie_frontend(
                superficie_id_frontend
            )
            superficie, created = SuperficieDental.objects.get_or_create(
                diente=diente, nombre=nombre_superficie
            )
            diagnostico = Diagnostico.objects.get(key=diagnostico_key, activo=True)
            area_superficie = superficie.areaanatomica
            if not diagnostico.areasrelacionadas.filter(area__key=area_superficie).exists():
                raise ValidationError(
                    f"El diagnóstico '{diagnostico.nombre}' no es aplicable al área '{area_superficie}'. "
                    f"Áreas válidas: {[a.key for a in diagnostico.areasrelacionadas.all()]}"
                )
            diagnostico_dental = DiagnosticoDental.objects.create(
                superficie=superficie, diagnostico_catalogo=diagnostico, **kwargs
            )

            return diagnostico_dental
        