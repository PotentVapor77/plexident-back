# api/odontogram/services/diagnostico_text_service.py

from typing import Iterable, List, Literal
from django.db.models import Prefetch

from api.odontogram.models import (
    Diagnostico,
    AreaAfectada,
    DiagnosticoAreaAfectada,
    DiagnosticoAtributoClinico,
    TipoAtributoClinico,
    OpcionAtributoClinico,
)


def _formatear_lista_nombres(items: List[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} y {items[1]}"
    return f"{', '.join(items[:-1])} y {items[-1]}"


def _obtener_areas_diagnostico(diagnostico: Diagnostico) -> List[str]:
    areas_rel = DiagnosticoAreaAfectada.objects.filter(
        diagnostico=diagnostico
    ).select_related("area")
    nombres = [rel.area.nombre for rel in areas_rel]

    seen = set()
    result = []
    for n in nombres:
        if n not in seen:
            seen.add(n)
            result.append(n)
    return result


def _resumir_areas(diagnosticos: Iterable[Diagnostico]) -> str:
    all_areas: List[str] = []
    for d in diagnosticos:  # ← sin tilde
        all_areas.extend(_obtener_areas_diagnostico(d))

    seen = set()
    unique = []
    for a in all_areas:
        if a not in seen:
            seen.add(a)
            unique.append(a)
    return _formatear_lista_nombres(unique)


def _obtener_categoria_dominante(diagnosticos: Iterable[Diagnostico]) -> str:
    for d in diagnosticos:
        if d.categoria and d.categoria.nombre:
            return d.categoria.nombre
    return "diagnósticos del odontograma"


def _construir_texto_un_diagnostico(d: Diagnostico) -> str:
    categoria = d.categoria.nombre if d.categoria else "Diagnóstico"
    nombre_diag = d.nombre or d.siglas or d.key
    areas = _obtener_areas_diagnostico(d)
    texto_areas = _formatear_lista_nombres(areas)

    if texto_areas:
        return f"Procedimiento para {categoria}: {nombre_diag} en {texto_areas}."
    return f"Procedimiento para {categoria}: {nombre_diag}."


def _construir_texto_multiples_diagnosticos(diagnosticos: List[Diagnostico]) -> str:
    categoria_dominante = _obtener_categoria_dominante(diagnosticos)
    nombres_diag = [d.nombre or d.siglas or d.key for d in diagnosticos]  # ← sin tilde
    texto_diag = _formatear_lista_nombres(nombres_diag)
    texto_areas = _resumir_areas(diagnosticos)

    if texto_areas:
        return (
            f"Procedimiento integral para {categoria_dominante}: "
            f"{texto_diag} en {texto_areas}."
        )
    return f"Procedimiento integral para {categoria_dominante}: {texto_diag}."


def construir_texto_procedimiento_desde_diagnosticos(
    identificadores: Iterable[str | int],
    modo: Literal["id", "key"] = "id",
) -> str:
    ids_list = [i for i in identificadores if i]
    if not ids_list:
        return ""

    if modo == "id":
        filtro = {"id__in": ids_list}
    else:
        filtro = {"key__in": ids_list}

    diagnosticos = list(
        Diagnostico.objects.filter(**filtro).select_related("categoria")
    )

    if not diagnosticos:
        return ""

    if len(diagnosticos) == 1:
        return _construir_texto_un_diagnostico(diagnosticos[0])

    return _construir_texto_multiples_diagnosticos(diagnosticos)