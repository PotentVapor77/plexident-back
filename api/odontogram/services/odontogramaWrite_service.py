from typing import List, Dict, Any
import uuid
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from api.odontogram.models import (
    Paciente,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma,
    Diagnostico,
)

User = get_user_model()


def _es_uuid_valido(valor: str) -> bool:
    """
    Devuelve True solo si valor es un UUID válido.
    Sirve para ignorar IDs temporales del frontend (Date.now()-random).
    """
    try:
        uuid.UUID(str(valor))
        return True
    except (ValueError, TypeError):
        return False


class OdontogramaWriteService:
    @transaction.atomic
    def guardar_odontograma_completo(
        self,
        paciente_id: str,
        odontologo_id: int,
        odontograma_data: Dict[str, Dict[str, List[Dict[str, Any]]]],
        
    ) -> Dict[str, Any]:
        """
        Guarda el odontograma completo de un paciente.

        Reglas:
        - Si viene un ID que es UUID válido -> intenta editar por ID.
        - Si no hay ID o el ID no es UUID válido -> usa equivalencia por attrs.
        - Si no existe ni por ID ni por attrs -> crea diagnóstico nuevo.
        """

        try:
            paciente = Paciente.objects.get(id=paciente_id)
            odontologo = User.objects.get(id=odontologo_id)
        except (Paciente.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Paciente u odontólogo no encontrado")

        resultado = {
            "paciente_id": str(paciente.id),
            "dientes_procesados": [],
            "diagnosticos_guardados": 0,
            "diagnosticos_modificados": 0,
            "errores": [],
        }

        version_id = uuid.uuid4()
        now = timezone.now()
        
        # Procesar cada diente
        for codigo_fdi, superficies_dict in odontograma_data.items():
            try:
                diente, created = Diente.objects.get_or_create(
                    paciente=paciente,
                    codigo_fdi=codigo_fdi,
                )
                resultado["dientes_procesados"].append(codigo_fdi)

                # Procesar cada superficie
                for nombre_superficie, diagnosticos_list in superficies_dict.items():
                    try:
                        superficie, _ = SuperficieDental.objects.get_or_create(
                            diente=diente,
                            nombre=nombre_superficie,
                        )

                        print("DEBUG diagnosticos_list:", diagnosticos_list)

                        # Procesar cada diagnóstico
                        for diag_data in diagnosticos_list:
                            try:
                                diagnostico_cat = Diagnostico.objects.get(
                                    key=diag_data["procedimientoId"],
                                    activo=True,
                                )

                                attrs = diag_data.get("secondaryOptions", {}) or {}
                                descripcion = diag_data.get("descripcion", "") or ""
                                diag_id = diag_data.get("id")

                                # 1) Si viene ID y es UUID válido, intentar EDITAR por ID
                                if diag_id and _es_uuid_valido(diag_id):
                                    try:
                                        diag_dental = DiagnosticoDental.objects.get(
                                            id=diag_id,
                                            superficie=superficie,
                                            diagnostico_catalogo=diagnostico_cat,
                                            activo=True,
                                        )
                                    except DiagnosticoDental.DoesNotExist:
                                        diag_dental = None

                                    if diag_dental:
                                        datos_anteriores = {
                                            "descripcion": diag_dental.descripcion,
                                            "atributos_clinicos": diag_dental.atributos_clinicos,
                                        }

                                        datos_nuevos = {
                                            "descripcion": descripcion,
                                            "atributos_clinicos": attrs,
                                        }

                                        ha_cambios = (
                                            datos_anteriores["descripcion"]
                                            != datos_nuevos["descripcion"]
                                            or datos_anteriores["atributos_clinicos"]
                                            != datos_nuevos["atributos_clinicos"]
                                        )

                                        if ha_cambios:
                                            diag_dental.descripcion = descripcion
                                            diag_dental.atributos_clinicos = attrs
                                            diag_dental.save()

                                            HistorialOdontograma.objects.create(
                                                diente=superficie.diente,
                                                tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO,
                                                descripcion=(
                                                    f"Diagnóstico {diagnostico_cat.nombre} "
                                                    f"modificado en {superficie.get_nombre_display()}"
                                                ),
                                                odontologo=odontologo,
                                                datos_anteriores=datos_anteriores,
                                                datos_nuevos=datos_nuevos,
                                                fecha=now,
                                                version_id=version_id,
                                            )
                                            resultado["diagnosticos_modificados"] += 1
                                            print(
                                                f"[DEBUG] Modificado con cambios: {diag_id}"
                                            )
                                        else:
                                            print(
                                                f"[DEBUG] Sin cambios, no se registra: {diag_id}"
                                            )

                                        continue

                                # 2) Editar por equivalencia
                                existente = DiagnosticoDental.objects.filter(
                                    superficie=superficie,
                                    diagnostico_catalogo=diagnostico_cat,
                                    atributos_clinicos=attrs,
                                    activo=True,
                                ).first()

                                if existente:
                                    datos_anteriores = {
                                        "descripcion": existente.descripcion,
                                        "atributos_clinicos": existente.atributos_clinicos,
                                    }

                                    datos_nuevos = {
                                        "descripcion": descripcion,
                                        "atributos_clinicos": attrs,
                                    }

                                    ha_cambios = (
                                        datos_anteriores["descripcion"]
                                        != datos_nuevos["descripcion"]
                                        or datos_anteriores["atributos_clinicos"]
                                        != datos_nuevos["atributos_clinicos"]
                                    )

                                    if ha_cambios:
                                        existente.descripcion = descripcion
                                        existente.atributos_clinicos = attrs
                                        existente.save()

                                        HistorialOdontograma.objects.create(
                                            diente=superficie.diente,
                                            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO,
                                            descripcion=(
                                                f"Diagnóstico {diagnostico_cat.nombre} "
                                                f"modificado en {superficie.get_nombre_display()}"
                                            ),
                                            odontologo=odontologo,
                                            datos_anteriores=datos_anteriores,
                                            datos_nuevos=datos_nuevos,
                                            fecha=now,
                                            version_id=version_id,
                                        )
                                        resultado["diagnosticos_modificados"] += 1
                                        print(
                                            f"[DEBUG] Modificado por attrs: {existente.id}"
                                        )
                                    else:
                                        print(
                                            f"[DEBUG] Sin cambios por attrs: {existente.id}"
                                        )

                                    continue

                                # 3) Alta nueva real
                                print(
                                    "DEBUG: creando nuevo diagnostico",
                                    diagnostico_cat.key,
                                    attrs,
                                )
                                diag_dental = DiagnosticoDental.objects.create(
                                    superficie=superficie,
                                    diagnostico_catalogo=diagnostico_cat,
                                    odontologo=odontologo,
                                    descripcion=descripcion,
                                    atributos_clinicos=attrs,
                                    estado_tratamiento=DiagnosticoDental.EstadoTratamiento.DIAGNOSTICADO,
                                )

                                HistorialOdontograma.objects.create(
                                    diente=diente,
                                    tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_AGREGADO,
                                    descripcion=(
                                        f"Diagnóstico {diagnostico_cat.nombre} agregado en "
                                        f"{superficie.get_nombre_display()}"
                                    ),
                                    odontologo=odontologo,
                                    datos_nuevos={
                                        "diagnostico": diagnostico_cat.key,
                                        "superficie": nombre_superficie,
                                        "atributos": attrs,
                                    },
                                    fecha=now,
                                    version_id=version_id,
                                )

                                resultado["diagnosticos_guardados"] += 1

                            except Diagnostico.DoesNotExist:
                                resultado["errores"].append(
                                    f"Diagnóstico {diag_data.get('procedimientoId')} no encontrado"
                                )
                            except Exception as e:
                                resultado["errores"].append(
                                    f"Error guardando diagnóstico en {codigo_fdi}/{nombre_superficie}: {str(e)}"
                                )

                    except Exception as e:
                        resultado["errores"].append(
                            f"Error procesando superficie {nombre_superficie}: {str(e)}"
                        )

            except Exception as e:
                resultado["errores"].append(
                    f"Error procesando diente {codigo_fdi}: {str(e)}"
                )

        total_cambios = (
            resultado["diagnosticos_guardados"] + resultado["diagnosticos_modificados"]
        )

        if total_cambios > 0 and resultado["dientes_procesados"]:
            primer_diente = Diente.objects.filter(
                paciente=paciente, codigo_fdi=resultado["dientes_procesados"][0]
            ).first()

            if primer_diente:
                odontograma_snapshot = {}

                for codigo_fdi, superficies_dict in odontograma_data.items():
                    odontograma_snapshot[codigo_fdi] = {}

                    for (
                        nombre_superficie,
                        diagnosticos_list,
                    ) in superficies_dict.items():
                        odontograma_snapshot[codigo_fdi][nombre_superficie] = []

                        for diag_data in diagnosticos_list:
                            try:
                                diagnostico_cat = (
                                    Diagnostico.objects.select_related("categoria")
                                    .prefetch_related("areas_relacionadas__area")
                                    .get(
                                        key=diag_data["procedimientoId"],
                                        activo=True,
                                    )
                                )

                                diag_enriquecido = {
                                    "id": diag_data.get("id"),
                                    "procedimientoId": diagnostico_cat.key,
                                    "key": diagnostico_cat.key,
                                    "nombre": diagnostico_cat.nombre,
                                    "siglas": diagnostico_cat.siglas,
                                    "colorHex": diagnostico_cat.simbolo_color,
                                    "categoria_nombre": diagnostico_cat.categoria.nombre,
                                    "categoria_color_key": diagnostico_cat.categoria.color_key,
                                    "prioridadKey": diagnostico_cat.categoria.prioridad_key,  # ← Frontend espera camelCase
                                    "prioridad": diagnostico_cat.prioridad,
                                    "afectaArea": list(
                                        diagnostico_cat.areas_relacionadas.values_list(
                                            "area__key", flat=True
                                        )
                                    ),
                                    "secondaryOptions": diag_data.get(
                                        "secondaryOptions", {}
                                    ),
                                    "descripcion": diag_data.get("descripcion", ""),
                                }

                                odontograma_snapshot[codigo_fdi][
                                    nombre_superficie
                                ].append(diag_enriquecido)
                            except Diagnostico.DoesNotExist:
                                # Si el diagnóstico no existe, mantener datos originales
                                odontograma_snapshot[codigo_fdi][
                                    nombre_superficie
                                ].append(diag_data)

                # Crear registro maestro del snapshot
                HistorialOdontograma.objects.create(
                    diente=primer_diente,
                    tipo_cambio=HistorialOdontograma.TipoCambio.SNAPSHOT_COMPLETO,
                    descripcion=(
                        f"Odontograma guardado: {resultado['diagnosticos_guardados']} diagnósticos nuevos, "
                        f"{resultado['diagnosticos_modificados']} modificados en "
                        f"{len(resultado['dientes_procesados'])} dientes"
                    ),
                    odontologo=odontologo,
                    datos_nuevos=odontograma_snapshot,
                    fecha=now,
                    version_id=version_id,
                )
                print(
                    f"[DEBUG] Snapshot completo enriquecido creado: version_id={version_id}"
                )

        resultado["version_id"] = str(version_id)
        resultado["tiene_cambios"] = total_cambios > 0

        # Invalidar caché
        cache_key = f"odontograma:completo:{paciente_id}"
        cache.delete(cache_key)

        return resultado
