
from typing import List, Dict, Any, Optional
import uuid
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from api.odontogram.models import (
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma,
)
from django.db.models import Prefetch

from api.odontogram.services.context_service import OperacionContexto

User = get_user_model()


class OdontogramaDiagnosticoService:
    @transaction.atomic
    def marcar_diagnostico_tratado(
        self, diagnostico_id: str, odontologo_id: int
    ) -> DiagnosticoDental:
        """
        Marca un diagnóstico como 'Tratado' y registra el cambio en el historial.
        """
        try:
            diagnostico = DiagnosticoDental.objects.select_for_update().get(
                id=diagnostico_id, activo=True
            )
            odontologo = User.objects.get(id=odontologo_id)
        except (DiagnosticoDental.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Diagnóstico u odontólogo no encontrado")

        datos_anteriores = {
            "estado_tratamiento": diagnostico.estado_tratamiento,
            "fecha_tratamiento": (
                diagnostico.fecha_tratamiento.isoformat()
                if diagnostico.fecha_tratamiento
                else None
            ),
        }

        # Actualizar estado y fecha
        diagnostico.estado_tratamiento = DiagnosticoDental.EstadoTratamiento.TRATADO
        diagnostico.fecha_tratamiento = timezone.now()
        diagnostico.save()

        datos_nuevos = {
            "estado_tratamiento": diagnostico.estado_tratamiento,
            "fecha_tratamiento": diagnostico.fecha_tratamiento.isoformat(),
        }

        # Crear registro en el historial
        HistorialOdontograma.objects.create(
            diente=diagnostico.diente,
            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_TRATADO,
            descripcion=f"Diagnóstico '{diagnostico.diagnostico_catalogo.nombre}' marcado como Tratado en la superficie {diagnostico.superficie.get_nombre_display()}",
            odontologo=odontologo,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
        )

        return diagnostico

    @transaction.atomic
    def eliminar_diagnostico(self, diagnostico_id: str, odontologo_id: int) -> bool:
        """
        Elimina un diagnóstico (soft delete) y registra en historial
        """
        try:
            diagnostico = DiagnosticoDental.objects.get(id=diagnostico_id)
            odontologo = User.objects.get(id=odontologo_id)
        except (DiagnosticoDental.DoesNotExist, User.DoesNotExist):
            return False

        paciente_id = str(diagnostico.superficie.diente.paciente.id)
        diente = diagnostico.superficie.diente

        # Guardar info del diagnóstico eliminado para la descripción
        diagnostico_nombre = diagnostico.diagnostico_catalogo.nombre
        superficie_nombre = diagnostico.superficie.get_nombre_display()

        # 1. Soft delete
        diagnostico.activo = False
        diagnostico.save()

        # 2. SIEMPRE crear registro simple de eliminación (SIN snapshot)
        print(f"[CONTEXTO] Eliminación individual - solo registro simple para paciente {paciente_id}")
        HistorialOdontograma.objects.create(
            diente=diente,
            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_ELIMINADO,
            descripcion=f"Diagnóstico '{diagnostico_nombre}' eliminado de {superficie_nombre}",
            odontologo=odontologo,
            datos_anteriores={
                'diagnostico_id': str(diagnostico.id),
                'diagnostico_nombre': diagnostico_nombre,
                'superficie': superficie_nombre,
                'superficie_id': diagnostico.superficie.nombre,
            },
            fecha=timezone.now(),
        )

        # 3. Invalidar caché (SIN snapshot)
        cache_key = f"odontograma:completo:{paciente_id}"
        cache.delete(cache_key)

        return True
        # 3. Si NO hay operación activa, crear snapshot completo
        print(f"[CONTEXTO] No hay operación activa, creando snapshot completo")
        
        version_id = uuid.uuid4()
        now = timezone.now()

        # 4. Obtener estado completo actualizado del odontograma
        odontograma_snapshot = {}

        dientes = (
            Diente.objects.filter(paciente_id=paciente_id)
            .prefetch_related(
                Prefetch(
                    "superficies",
                    queryset=SuperficieDental.objects.prefetch_related(
                        Prefetch(
                            "diagnosticos",
                            queryset=DiagnosticoDental.objects.filter(
                                activo=True
                            )
                            .select_related(
                                "diagnostico_catalogo",
                                "diagnostico_catalogo__categoria",
                            )
                            .prefetch_related(
                                "diagnostico_catalogo__areas_relacionadas__area"
                            ),
                        )
                    ),
                )
            )
            .order_by("codigo_fdi")
        )

        # Construir snapshot completo
        total_diagnosticos = 0
        for diente_obj in dientes:
            codigo_fdi = diente_obj.codigo_fdi
            odontograma_snapshot[codigo_fdi] = {}

            for superficie in diente_obj.superficies.all():
                diagnosticos_activos = list(superficie.diagnosticos.all())
                if diagnosticos_activos:
                    odontograma_snapshot[codigo_fdi][superficie.nombre] = []

                    for diag_dental in diagnosticos_activos:
                        diag_enriquecido = {
                            "id": str(diag_dental.id),
                            "procedimientoId": diag_dental.diagnostico_catalogo.key,
                            "key": diag_dental.diagnostico_catalogo.key,
                            "nombre": diag_dental.diagnostico_catalogo.nombre,
                            "siglas": diag_dental.diagnostico_catalogo.siglas,
                            "colorHex": diag_dental.diagnostico_catalogo.simbolo_color,
                            "prioridad": diag_dental.diagnostico_catalogo.prioridad,
                            "categoria_nombre": diag_dental.diagnostico_catalogo.categoria.nombre,
                            "categoria_color_key": diag_dental.diagnostico_catalogo.categoria.color_key,
                            "prioridadKey": diag_dental.diagnostico_catalogo.categoria.prioridad_key,
                            "afectaArea": list(
                                diag_dental.diagnostico_catalogo.areas_relacionadas.values_list(
                                    "area__key", flat=True
                                )
                            ),
                            "secondaryOptions": diag_dental.atributos_clinicos,
                            "descripcion": diag_dental.descripcion,
                        }
                        odontograma_snapshot[codigo_fdi][superficie.nombre].append(
                            diag_enriquecido
                        )
                        total_diagnosticos += 1

        # 5. Crear snapshot completo
        primer_diente = dientes.first()
        if primer_diente:
            HistorialOdontograma.objects.create(
                diente=primer_diente,
                tipo_cambio=HistorialOdontograma.TipoCambio.SNAPSHOT_COMPLETO,
                descripcion=(
                    f"Eliminado '{diagnostico_nombre}' de {superficie_nombre}. "
                    f"Odontograma actualizado: {total_diagnosticos} diagnósticos en "
                    f"{len(odontograma_snapshot)} dientes"
                ),
                odontologo=odontologo,
                datos_nuevos=odontograma_snapshot,
                fecha=now,
                version_id=version_id,
            )

        # 6. Invalidar caché
        cache_key = f"odontograma:completo:{paciente_id}"
        cache.delete(cache_key)

        return True



    @transaction.atomic
    def eliminar_diagnosticos_batch(
        self, diagnosticoids: List[str], odontologoid: int
    ) -> Dict[str, Any]:
        """
        Elimina múltiples diagnósticos en una sola transacción
        y crea UN ÚNICO snapshot del estado resultante
        """
        # 1. Validar usuario
        try:
            odontologo = User.objects.get(id=odontologoid)
        except User.DoesNotExist:
            raise ValidationError("Odontólogo no encontrado")

        # 2. Validar que hay IDs
        if not diagnosticoids:
            return {"success": False, "error": "No hay diagnósticos para eliminar"}

        # 3. Obtener todos los diagnósticos a eliminar
        diagnosticos = DiagnosticoDental.objects.filter(
            id__in=diagnosticoids, activo=True
        ).select_related("diagnostico_catalogo", "diagnostico_catalogo__categoria", "superficie__diente__paciente")

        if not diagnosticos.exists():
            return {"success": False, "error": "No se encontraron diagnósticos activos"}

        # 4. Obtener info del paciente
        primer_diagnostico = diagnosticos.first()
        paciente_id = str(primer_diagnostico.superficie.diente.paciente.id)

        # 5. Generar version_id
        version_id = uuid.uuid4()
        now = timezone.now()

        # 6. Construir descripción
        eliminados = []
        for diag in diagnosticos:
            eliminados.append(
                f"{diag.diagnostico_catalogo.nombre} ({diag.superficie.get_nombre_display()})"
            )

        # 7. Soft delete
        diagnosticos.update(activo=False)

        # 8. Obtener snapshot actualizado
        odontograma_snapshot = {}
        dientes = (
            Diente.objects.filter(paciente_id=paciente_id)
            .prefetch_related(
                Prefetch(
                    "superficies",
                    queryset=SuperficieDental.objects.prefetch_related(
                        Prefetch(
                            "diagnosticos",
                            queryset=DiagnosticoDental.objects.filter(activo=True)
                            .select_related(
                                "diagnostico_catalogo",
                                "diagnostico_catalogo__categoria",
                            )
                            .prefetch_related(
                                "diagnostico_catalogo__areas_relacionadas__area"
                            ),
                        )
                    ),
                )
            )
            .order_by("codigo_fdi")
        )

        # 9. Construir snapshot
        total_diagnosticos = 0
        for diente_obj in dientes:
            codigo_fdi = diente_obj.codigo_fdi
            odontograma_snapshot[codigo_fdi] = {}

            for superficie in diente_obj.superficies.all():
                diagnosticos_activos = list(superficie.diagnosticos.all())

                if diagnosticos_activos:
                    odontograma_snapshot[codigo_fdi][superficie.nombre] = []

                    for diag_dental in diagnosticos_activos:
                        diag_enriquecido = {
                            "id": str(diag_dental.id),
                            "procedimientoId": diag_dental.diagnostico_catalogo.key,
                            "key": diag_dental.diagnostico_catalogo.key,
                            "nombre": diag_dental.diagnostico_catalogo.nombre,
                            "siglas": diag_dental.diagnostico_catalogo.siglas,
                            "colorHex": diag_dental.diagnostico_catalogo.simbolo_color,
                            "prioridad": diag_dental.diagnostico_catalogo.prioridad,
                            "categoria_nombre": diag_dental.diagnostico_catalogo.categoria.nombre,
                            "categoria_color_key": diag_dental.diagnostico_catalogo.categoria.color_key,
                            "prioridadKey": diag_dental.diagnostico_catalogo.categoria.prioridad_key,
                            "afectaArea": list(
                                diag_dental.diagnostico_catalogo.areas_relacionadas.values_list(
                                    "area__key", flat=True
                                )
                            ),
                            "secondaryOptions": diag_dental.atributos_clinicos,
                            "descripcion": diag_dental.descripcion,
                        }
                        odontograma_snapshot[codigo_fdi][superficie.nombre].append(
                            diag_enriquecido
                        )
                        total_diagnosticos += 1

        # 10. Crear historial
        primer_diente = dientes.first()
        if primer_diente:
            descripcion = (
                f"Eliminados {len(eliminados)} diagnóstico(s): "
                f"{', '.join(eliminados[:3])}{' ...' if len(eliminados) > 3 else ''}. "
                f"Odontograma actualizado: {total_diagnosticos} diagnósticos en {len(odontograma_snapshot)} dientes"
            )

            HistorialOdontograma.objects.create(
                diente=primer_diente,
                tipo_cambio=HistorialOdontograma.TipoCambio.SNAPSHOT_COMPLETO,
                descripcion=descripcion,
                odontologo=odontologo,
                datos_nuevos=odontograma_snapshot,
                fecha=now,
                version_id=version_id,
            )

        # 11. Invalidar caché
        cache_key = f"odontograma_completo_{paciente_id}"
        cache.delete(cache_key)

        return {
            "success": True,
            "eliminados": len(eliminados),
            "versionid": str(version_id),
            "descripcion": descripcion,
        }


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
        """
        Actualiza un diagnóstico y registra cambios en historial
        """
        try:
            diagnostico = DiagnosticoDental.objects.select_for_update().get(
                id=diagnostico_id, activo=True
            )
            if odontologo_id:
                odontologo = User.objects.get(id=odontologo_id)
            else:
                odontologo = diagnostico.odontologo
        except (DiagnosticoDental.DoesNotExist, User.DoesNotExist):
            return None

        # Guardar datos anteriores para historial
        datos_anteriores = {
            "descripcion": diagnostico.descripcion,
            "atributos_clinicos": diagnostico.atributos_clinicos,
            "estado_tratamiento": diagnostico.estado_tratamiento,
            "prioridad_asignada": diagnostico.prioridad_asignada,
            "fecha_tratamiento": diagnostico.fecha_tratamiento,
            "diagnostico_catalogo_id": diagnostico.diagnostico_catalogo_id,
        }

        # Actualizar campos
        if descripcion is not None:
            diagnostico.descripcion = descripcion
        if atributos_clinicos is not None:
            # Merge con atributos existentes
            current_attrs = diagnostico.atributos_clinicos or {}
            current_attrs.update(atributos_clinicos)
            diagnostico.atributos_clinicos = current_attrs
        if estado_tratamiento is not None:
            diagnostico.estado_tratamiento = estado_tratamiento
        if prioridad_asignada is not None:
            if not 1 <= prioridad_asignada <= 5:
                raise ValidationError("Prioridad debe estar entre 1 y 5")
            diagnostico.prioridad_asignada = prioridad_asignada
        if fecha_tratamiento is not None:
            diagnostico.fecha_tratamiento = fecha_tratamiento
        if diagnostico_catalogo_id is not None:
            diagnostico.diagnostico_catalogo_id = diagnostico_catalogo_id
        if odontologo_id is not None:
            diagnostico.odontologo_id = odontologo_id

        diagnostico.save()

        # Crear historial de cambios
        datos_nuevos = {
            "descripcion": diagnostico.descripcion,
            "atributos_clinicos": diagnostico.atributos_clinicos,
            "estado_tratamiento": diagnostico.estado_tratamiento,
            "prioridad_asignada": diagnostico.prioridad_asignada,
            "fecha_tratamiento": diagnostico.fecha_tratamiento,
            "diagnostico_catalogo_id": diagnostico.diagnostico_catalogo_id,
        }

        HistorialOdontograma.objects.create(
            diente=diagnostico.diente,
            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO,
            descripcion=f"Diagnóstico {diagnostico.diagnostico_catalogo.nombre} modificado",
            odontologo=odontologo,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
        )

        return diagnostico
