# api/odontogram/services/indice_caries_service.py
"""
Servicio independiente para cálculos de índices de caries
Separado para evitar importaciones circulares
"""

from collections import defaultdict
from typing import Dict, Any
from django.db import transaction
from api.odontogram.models import (
    Diente,
    DiagnosticoDental,
    Diagnostico,
    IndiceCariesSnapshot,
)
from api.odontogram.constants import FDIConstants
import logging

logger = logging.getLogger(__name__)

CARIES_KEYS = {"caries"}
OBTURADO_KEYS = {
    "obturacion",
    "sellante_realizado",
    "corona_realizada",
    "protesis_fija_realizada",
    "protesis_removible_realizada",
}
AUSENTE_KEYS = {"ausente"}


class IndiceCariesService:

    @staticmethod
    def calcular_indices_paciente(paciente_id: str) -> Dict[str, Any]:
        """
        Calcula índices CPO y CPO-CEO
        """
        
        dientes = Diente.objects.filter(
            paciente_id=paciente_id,
        )
        
        diagnosticos = (
            DiagnosticoDental.objects.filter(
                superficie__diente__paciente_id=paciente_id,
                activo=True,
            )
            
            .select_related(
                "diagnostico_catalogo",
                "superficie__diente",
                "diagnostico_catalogo__categoria",
            )
        )
        logger.info(
                f"[CPO] Diagnósticos activos encontrados: {diagnosticos.count()}"
            )
        indices = {
            "permanente": {"C": 0, "P": 0, "O": 0, "total": 0},
            "temporal": {"c": 0, "e": 0, "o": 0, "total": 0},
        }

        dx_por_diente = defaultdict(list)
        for dx in diagnosticos:
            dx_por_diente[dx.superficie.diente_id].append(dx)

        for diente in dientes:
            info = FDIConstants.obtener_info_fdi(diente.codigo_fdi)
            if not info:
                continue
            logger.debug(f"[CPO] Diente {diente.codigo_fdi} info FDI: {info}")
            denticion = info["denticion"] 
            dx_diente = dx_por_diente.get(diente.id, [])
            logger.debug(
            f"[CPO] Diente {diente.codigo_fdi} dentición={denticion} "
            f"dx_count={len(dx_diente)}"
        )
            if denticion == "permanente":
                IndiceCariesService._acumular_cpo(diente, dx_diente, indices["permanente"])
            else:
                IndiceCariesService._acumular_ceo(diente, dx_diente, indices["temporal"])

        p = indices["permanente"]
        p["total"] = p["C"] + p["P"] + p["O"]

        t = indices["temporal"]
        t["total"] = t["c"] + t["e"] + t["o"]
        logger.info(f"[CPO] Resultado índices: {indices}")
        return indices

    @staticmethod
    def _acumular_cpo(diente, dx_diente, acumulador):
        logger.debug(
        f"[CPO] _acumular_cpo diente={diente.codigo_fdi} "
        f"dx={[dx.diagnostico_catalogo.key for dx in dx_diente]}"
    )

        tiene_caries = False
        tiene_obturado = False
        tiene_perdida_por_carias = False

        for dx in dx_diente:
            key = dx.diagnostico_catalogo.key
            cat = dx.diagnostico_catalogo.categoria.key 
            
            logger.debug(f"[CPO]   dx key={key} cat={cat}")

            if key in {"caries"} and cat == "patologia_activa":
                tiene_caries = True

            if key in {
                "obturacion",
                "sellante_realizado",
                "corona_realizada",
                "protesis_fija_realizada",
                "protesis_removible_realizada",
            } and cat == "tratamiento_realizado":
                tiene_obturado = True

            # Perdidas por caries registradas como tratamiento realizado
            if key in {"extraccion_otra_causa", "perdida_otra_causa"} and cat == "tratamiento_realizado":
                tiene_perdida_por_carias = True

            # Ausencia (diagnóstico de ausencia en catálogo)
            if key == "ausente" and cat == "ausencia":
                tiene_perdida_por_carias = True

        # 1) P: cualquier forma de pérdida por caries / extracción
        if tiene_perdida_por_carias or diente.ausente:
            acumulador["P"] += 1
            return

        # 2) C: si hay caries, aunque también haya obturación
        if tiene_caries:
            acumulador["C"] += 1
            return

        # 3) O: restaurado sin caries
        if tiene_obturado:
            acumulador["O"] += 1

    @staticmethod
    def _acumular_ceo(diente, dx_diente, acumulador: dict):
        """
        ceo (temporal) – placeholder:
        - c: caries
        - e: extracción indicada
        - o: obturado
        """
        # Lógica temporal - implementar según necesidad
        return
    
    @staticmethod
    def crear_snapshot_indices(paciente_id: str, version_id=None) -> IndiceCariesSnapshot:
        """
        Calcula índices actuales y los guarda como snapshot.
        """
        logger.info(f"[CPO] Creando snapshot para paciente={paciente_id} version={version_id}")
        indices = IndiceCariesService.calcular_indices_paciente(paciente_id)
        logger.info(f"[CPO] Índices calculados antes de snapshot: {indices}")
        perm = indices["permanente"]
        temp = indices["temporal"]

        snapshot = IndiceCariesSnapshot.objects.create(
            paciente_id=paciente_id,
            version_id=version_id,
            cpo_c=perm["C"],
            cpo_p=perm["P"],
            cpo_o=perm["O"],
            cpo_total=perm["total"],
            ceo_c=temp["c"],
            ceo_e=temp["e"],
            ceo_o=temp["o"],
            ceo_total=temp["total"],
        )
        logger.info(
        f"[CPO] Snapshot creado id={snapshot.id} "
        f"CPO=({snapshot.cpo_c},{snapshot.cpo_p},{snapshot.cpo_o},{snapshot.cpo_total}) "
        f"ceo=({snapshot.ceo_c},{snapshot.ceo_e},{snapshot.ceo_o},{snapshot.ceo_total})"
    )
        
        return snapshot