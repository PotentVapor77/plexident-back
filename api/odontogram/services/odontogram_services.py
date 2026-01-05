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
            return self._write.guardar_odontograma_completo(
                paciente_id=paciente_id,
                odontologo_id=odontologo_id,
                odontograma_data=odontograma_data,
            )

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
        
        
class IndiceCariesService:

    @staticmethod
    def calcular_indices_paciente(paciente_id: str):
        """
        Calcula índices CPO y CPO-CEO
        """
        logger.info(f"[CPO] Calculando índices para paciente {paciente_id}")
        dientes = Diente.objects.filter(
            paciente_id=paciente_id,
        )
        logger.info(f"[CPO] Dientes activos encontrados: {dientes.count()}")
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
            denticion = info["denticion"]  # "permanente" o "temporal"
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
        tiene_perdida_por_caries = False

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
                tiene_perdida_por_caries = True

            # Ausencia (diagnóstico de ausencia en catálogo)
            if key == "ausente" and cat == "ausencia":
                tiene_perdida_por_caries = True

        # 1) P: cualquier forma de pérdida por caries / extracción
        if tiene_perdida_por_caries or diente.ausente:
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
        # Recuerda Nava de Mapear caries extraccion o lo que sea no te olvides
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
    
    
class IndicadoresSaludBucalService:

    @staticmethod
    def calcular_promedios(indicadores: IndicadoresSaludBucal):
        placa_vals = [
            indicadores.pieza_16_placa,
            indicadores.pieza_11_placa,
            indicadores.pieza_26_placa,
            indicadores.pieza_36_placa,
            indicadores.pieza_31_placa,
            indicadores.pieza_46_placa,
        ]
        calculo_vals = [
            indicadores.pieza_16_calculo,
            indicadores.pieza_11_calculo,
            indicadores.pieza_26_calculo,
            indicadores.pieza_36_calculo,
            indicadores.pieza_31_calculo,
            indicadores.pieza_46_calculo,
        ]
        placa = [v for v in placa_vals if v is not None]
        calculo = [v for v in calculo_vals if v is not None]

        indicadores.ohi_promedio_placa = sum(placa) / len(placa) if placa else None
        indicadores.ohi_promedio_calculo = sum(calculo) / len(calculo) if calculo else None
        indicadores.save()
        return indicadores