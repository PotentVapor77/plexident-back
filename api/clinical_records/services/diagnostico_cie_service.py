# api/clinical_records/services/diagnostico_cie_service.py
import logging
from typing import List, Dict, Any, Optional
from django.utils import timezone
from api.odontogram.models import DiagnosticoDental, HistorialOdontograma
from api.clinical_records.models import ClinicalRecord, DiagnosticoCIEHistorial
from django.core.exceptions import ValidationError
from collections import OrderedDict
from django.db.models import Q

logger = logging.getLogger(__name__)


class DiagnosticosCIEService:
    """Servicio para cargar y gestionar diagnósticos CIE-10"""

    @staticmethod
    def obtener_diagnosticos_paciente(paciente_id: str, tipo_carga: str = 'nuevos') -> List[Dict[str, Any]]:
        """
        Obtiene diagnósticos del paciente según el tipo de carga
        """
        try:
            if tipo_carga == 'nuevos':
                return DiagnosticosCIEService.obtener_diagnosticos_nuevos(paciente_id)
            else:
                return DiagnosticosCIEService.obtener_diagnosticos_todos(paciente_id)
        except Exception as e:
            logger.error(f"Error en obtener_diagnosticos_paciente: {str(e)}")
            return []

    @staticmethod
    def obtener_diagnosticos_nuevos(paciente_id: str) -> List[Dict[str, Any]]:
        try:
            # Obtener TODOS los diagnósticos del paciente
            todos_diagnosticos = DiagnosticoDental.objects.filter(
                superficie__diente__paciente_id=paciente_id,
                activo=True,
            ).select_related(
                'diagnostico_catalogo',
                'superficie',
                'superficie__diente',
                'superficie__diente__paciente',
                'odontologo',
            )

            # 1. Obtener todos los historiales del paciente
            historiales_paciente = ClinicalRecord.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).values_list('id', flat=True)

            # 2. Obtener diagnósticos CIE ya cargados en esos historiales
            diagnosticos_cargados = DiagnosticoCIEHistorial.objects.filter(
                historial_clinico_id__in=historiales_paciente,
                activo=True
            ).select_related(
                'diagnostico_dental__superficie__diente',
                'diagnostico_dental__diagnostico_catalogo'
            )

            # Crear un conjunto de claves únicas (diente_fdi + codigo_cie) ya cargadas
            claves_cargadas = set()
            for diag_cargado in diagnosticos_cargados:
                diente_fdi = (
                    diag_cargado.diagnostico_dental.superficie.diente.codigo_fdi
                    if diag_cargado.diagnostico_dental and
                    diag_cargado.diagnostico_dental.superficie and
                    diag_cargado.diagnostico_dental.superficie.diente
                    else ""
                )
                codigo_cie = (
                    diag_cargado.diagnostico_dental.diagnostico_catalogo.codigo_icd10
                    if diag_cargado.diagnostico_dental and
                    diag_cargado.diagnostico_dental.diagnostico_catalogo
                    else ""
                )
                if diente_fdi and codigo_cie:
                    clave = f"{diente_fdi}_{codigo_cie}"
                    claves_cargadas.add(clave)

            logger.debug(f"DEBUG - Claves cargadas: {claves_cargadas}")

            # 3. Filtrar diagnósticos "nuevos" - excluyendo por diente+código CIE
            diagnosticos_nuevos = []
            for diag in todos_diagnosticos:
                diente_fdi = (
                    diag.superficie.diente.codigo_fdi
                    if diag.superficie and diag.superficie.diente else ""
                )
                codigo_cie = (
                    diag.diagnostico_catalogo.codigo_icd10
                    if diag.diagnostico_catalogo else ""
                )

                if not diente_fdi or not codigo_cie:
                    continue

                clave_diag = f"{diente_fdi}_{codigo_cie}"

                if clave_diag not in claves_cargadas:
                    diagnosticos_nuevos.append(diag)

            logger.debug(f"DEBUG - Diagnósticos nuevos después de filtrar: {len(diagnosticos_nuevos)}")

            # Ordenar por fecha (más recientes primero)
            diagnosticos_nuevos.sort(
                key=lambda x: x.fecha if x.fecha else timezone.now(),
                reverse=True
            )

            # Agrupar por (diente_fdi, codigo_cie) para evitar duplicados en la respuesta
            agrupados: dict[tuple[str, str], DiagnosticoDental] = OrderedDict()
            for diag in diagnosticos_nuevos:
                diente_fdi = (
                    diag.superficie.diente.codigo_fdi
                    if diag.superficie and diag.superficie.diente else ""
                )
                codigo_cie = (
                    diag.diagnostico_catalogo.codigo_icd10
                    if diag.diagnostico_catalogo else ""
                )
                clave = (diente_fdi, codigo_cie)

                if clave not in agrupados:
                    agrupados[clave] = diag

            diagnosticos_unicos = list(agrupados.values())[:50]

            return DiagnosticosCIEService.formatear_diagnosticos(diagnosticos_unicos)
        except Exception as e:
            logger.error(f"Error en obtener_diagnosticos_nuevos: {str(e)}")
            return []

    @staticmethod
    def obtener_diagnosticos_todos(paciente_id: str) -> List[Dict[str, Any]]:
        try:
            diagnosticos = DiagnosticoDental.objects.filter(
                superficie__diente__paciente_id=paciente_id,
                activo=True,
            ).select_related(
                'diagnostico_catalogo',
                'superficie',
                'superficie__diente',
                'superficie__diente__paciente',
                'odontologo',
            ).order_by('-fecha')

            from collections import OrderedDict
            agrupados: dict[tuple[str, str], DiagnosticoDental] = OrderedDict()

            for diag in diagnosticos:
                diente_fdi = (
                    diag.superficie.diente.codigo_fdi
                    if diag.superficie and diag.superficie.diente else ""
                )
                codigo_cie = (
                    diag.diagnostico_catalogo.codigo_icd10
                    if diag.diagnostico_catalogo else ""
                )
                clave = (diente_fdi, codigo_cie)

                if clave not in agrupados:
                    agrupados[clave] = diag

            diagnosticos_unicos = list(agrupados.values())

            return DiagnosticosCIEService.formatear_diagnosticos(diagnosticos_unicos)
        except Exception as e:
            logger.error(f"Error en obtener_diagnosticos_todos: {str(e)}")
            return []

    @staticmethod
    def formatear_diagnosticos(diagnosticos_queryset) -> List[Dict[str, Any]]:
        """
        Formatea diagnósticos para el frontend.
        Nota: estos diagnósticos aún no tienen historial asociado, por lo que
        no tienen codigo_cie_personalizado. Se incluyen los campos vacíos para
        mantener estructura consistente con obtener_diagnosticos_historial().
        """
        diagnosticos_formateados: list[dict[str, Any]] = []

        for diag in diagnosticos_queryset:
            superficie_nombre = diag.superficie.get_nombre_display() if diag.superficie else ""
            diente_fdi = diag.superficie.diente.codigo_fdi if diag.superficie and diag.superficie.diente else ""
            fecha_diagnostico = diag.fecha.isoformat() if diag.fecha else ""

            if diag.diagnostico_catalogo:
                codigo_cie = diag.diagnostico_catalogo.codigo_icd10
                diagnostico_nombre = diag.diagnostico_catalogo.nombre
                diagnostico_siglas = diag.diagnostico_catalogo.siglas
            else:
                codigo_cie = ""
                diagnostico_nombre = "Sin diagnóstico"
                diagnostico_siglas = ""

            diagnosticos_formateados.append({
                'diagnostico_dental_id': str(diag.id),
                'diagnostico_nombre': diagnostico_nombre,
                'diagnostico_siglas': diagnostico_siglas,
                'codigo_cie': codigo_cie,
                # Campos de personalización (vacíos aquí, se rellenan cuando ya están en un historial)
                'codigo_cie_original': codigo_cie,
                'codigo_cie_personalizado': None,
                'tiene_codigo_personalizado': False,
                'diente_fdi': diente_fdi,
                'superficie_nombre': superficie_nombre,
                'fecha_diagnostico': fecha_diagnostico,
                'tipo_cie': 'PRE',  # por defecto Presuntivo
                'activo': diag.activo,
            })

        return diagnosticos_formateados

    @staticmethod
    def cargar_diagnosticos_a_historial(
        historial_clinico: ClinicalRecord,
        diagnosticos_data: List[Dict[str, Any]],
        tipo_carga: str,
        usuario
    ) -> Dict[str, Any]:
        """
        Carga diagnósticos CIE-10 al historial clínico.
        Ahora persiste codigo_cie_personalizado si el historial está en BORRADOR.
        """
        try:
            if historial_clinico.estado == 'CERRADO':
                raise ValueError('No se pueden agregar diagnósticos a un historial cerrado')

            # Solo se permite personalizar códigos en BORRADOR
            puede_personalizar = historial_clinico.estado == 'BORRADOR'

            # Obtener diagnósticos previos para este historial
            diagnosticos_previos = DiagnosticoCIEHistorial.objects.filter(
                historial_clinico=historial_clinico,
                activo=True
            )

            # Marcar los previos como inactivos si estamos en modo "nuevos"
            if tipo_carga == 'nuevos':
                for diag_previo in diagnosticos_previos:
                    diag_previo.activo = False
                    diag_previo.actualizado_por = usuario
                    diag_previo.save()

            diagnosticos_guardados = []
            diagnosticos_ids = set()

            for diag_data in diagnosticos_data:
                diagnostico_dental_id = diag_data.get('diagnostico_dental_id')
                tipo_cie = diag_data.get('tipo_cie', 'PRE')
                # NUEVO: código personalizado enviado por el profesional
                codigo_personalizado = diag_data.get('codigo_cie_personalizado', None)

                try:
                    diagnostico_dental = DiagnosticoDental.objects.get(
                        id=diagnostico_dental_id,
                        activo=True
                    )

                    if not diagnostico_dental.diagnostico_catalogo or not diagnostico_dental.diagnostico_catalogo.codigo_icd10:
                        logger.warning(f"Diagnóstico {diagnostico_dental_id} no tiene código CIE, saltando")
                        continue

                    diag_existente = DiagnosticoCIEHistorial.objects.filter(
                        historial_clinico=historial_clinico,
                        diagnostico_dental=diagnostico_dental
                    ).first()

                    if diag_existente:
                        diag_existente.tipo_cie = tipo_cie
                        diag_existente.activo = True
                        diag_existente.actualizado_por = usuario
                        # NUEVO: actualizar código personalizado solo en BORRADOR
                        if puede_personalizar:
                            if codigo_personalizado and codigo_personalizado.strip():
                                diag_existente.codigo_cie_personalizado = codigo_personalizado.strip().upper()
                            codigo_personalizado = diag_data.get('codigo_cie_personalizado')  # None si no viene

                            if puede_personalizar:
                                if codigo_personalizado is not None:  # Solo tocar si fue enviado explícitamente
                                    if codigo_personalizado.strip():
                                        diag_existente.codigo_cie_personalizado = codigo_personalizado.strip().upper()
                                    else:
                                        diag_existente.codigo_cie_personalizado = None 
                        diag_existente.save()
                        diag_cie = diag_existente
                    else:
                        # NUEVO: incluir codigo_cie_personalizado al crear
                        crear_kwargs = {
                            'historial_clinico': historial_clinico,
                            'diagnostico_dental': diagnostico_dental,
                            'tipo_cie': tipo_cie,
                            'creado_por': usuario,
                            'activo': True,
                        }
                        if puede_personalizar and codigo_personalizado and codigo_personalizado.strip():
                            crear_kwargs['codigo_cie_personalizado'] = codigo_personalizado.strip().upper()

                        diag_cie = DiagnosticoCIEHistorial.objects.create(**crear_kwargs)

                    diagnosticos_guardados.append(diag_cie)
                    diagnosticos_ids.add(str(diagnostico_dental_id))

                except DiagnosticoDental.DoesNotExist:
                    logger.warning(f"Diagnóstico dental {diagnostico_dental_id} no encontrado")
                    continue

            # Si estamos en modo "todos", mantener los anteriores activos también
            if tipo_carga == 'todos':
                for diag_previo in diagnosticos_previos:
                    if str(diag_previo.diagnostico_dental_id) not in diagnosticos_ids:
                        diag_previo.activo = True
                        diag_previo.actualizado_por = usuario
                        diag_previo.save()
                        diagnosticos_guardados.append(diag_previo)

            diagnosticos_ids_set = set()
            for diag_data in diagnosticos_data:
                diagnostico_dental_id = diag_data.get('diagnostico_dental_id')
                if diagnostico_dental_id in diagnosticos_ids_set:
                    logger.warning(f"Diagnóstico duplicado: {diagnostico_dental_id}")
                    continue
                diagnosticos_ids_set.add(diagnostico_dental_id)

            historial_clinico.diagnosticos_cie_cargados = len(diagnosticos_guardados) > 0
            historial_clinico.tipo_carga_diagnosticos = tipo_carga
            historial_clinico.save()

            logger.info(
                f"{len(diagnosticos_guardados)} diagnósticos CIE cargados "
                f"en historial {historial_clinico.id} (tipo: {tipo_carga})"
            )

            return {
                'success': True,
                'total_diagnosticos': len(diagnosticos_guardados),
                'tipo_carga': tipo_carga,
                'diagnosticos': [
                    {
                        'id': diag.id,
                        'diagnostico_dental_id': str(diag.diagnostico_dental.id),
                        'diagnostico_nombre': diag.nombre_diagnostico,
                        # NUEVO: devolver código efectivo y campos adicionales
                        'codigo_cie': diag.codigo_cie_efectivo,
                        'codigo_cie_original': diag.codigo_cie_original,
                        'codigo_cie_personalizado': diag.codigo_cie_personalizado,
                        'tiene_codigo_personalizado': diag.tiene_codigo_personalizado,
                        'diente_fdi': diag.diente_fdi,
                        'tipo_cie': diag.tipo_cie,
                        'activo': diag.activo,
                    }
                    for diag in diagnosticos_guardados
                ]
            }

        except Exception as e:
            logger.error(f"Error cargando diagnósticos CIE: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def obtener_diagnosticos_historial(historial_id: str) -> List[Dict[str, Any]]:
        """
        Devuelve diagnósticos CIE del historial.
        Ahora incluye campos de personalización de código CIE-10.
        """
        diagnosticos = DiagnosticoCIEHistorial.objects.filter(
            historial_clinico_id=historial_id,
            activo=True
        ).select_related(
            "diagnostico_dental",
            "diagnostico_dental__diagnostico_catalogo",
            "diagnostico_dental__superficie",
            "diagnostico_dental__superficie__diente",
        ).order_by("diagnostico_dental__diagnostico_catalogo__nombre")

        return [
            {
                "id": diag.id,
                "diagnostico_dental_id": diag.diagnostico_dental.id,
                "diagnostico_nombre": diag.nombre_diagnostico,
                "diagnostico_siglas": diag.diagnostico_dental.diagnostico_catalogo.siglas,
                # NUEVO: código efectivo (personalizado si existe, catálogo si no)
                "codigo_cie": diag.codigo_cie_efectivo,
                "codigo_cie_original": diag.codigo_cie_original,
                "codigo_cie_personalizado": diag.codigo_cie_personalizado,
                "tiene_codigo_personalizado": diag.tiene_codigo_personalizado,
                "diente_fdi": diag.diente_fdi,
                "superficie_nombre": diag.diagnostico_dental.superficie.get_nombre_display(),
                "fecha_diagnostico": diag.diagnostico_dental.fecha,
                "tipo_cie": diag.tipo_cie,
                "tipo_cie_display": diag.get_tipo_cie_display(),
                "activo": diag.activo,
            }
            for diag in diagnosticos
        ]

    @staticmethod
    def eliminar_diagnostico_individual(
        diagnostico_cie_id: str,
        usuario
    ) -> Dict[str, Any]:
        """
        Elimina un diagnóstico CIE individual del historial (eliminación lógica)
        """
        try:
            diagnostico = DiagnosticoCIEHistorial.objects.get(
                id=diagnostico_cie_id,
                activo=True
            )

            if diagnostico.historial_clinico.estado == 'CERRADO':
                raise ValidationError(
                    'No se pueden modificar diagnósticos de un historial cerrado'
                )

            diagnostico.activo = False
            diagnostico.actualizado_por = usuario
            diagnostico.save()

            logger.info(
                f"Diagnóstico CIE {diagnostico_cie_id} eliminado del "
                f"historial {diagnostico.historial_clinico.id} por {usuario.username}"
            )

            return {
                'success': True,
                'message': 'Diagnóstico eliminado exitosamente',
                'diagnostico_id': str(diagnostico_cie_id)
            }

        except DiagnosticoCIEHistorial.DoesNotExist:
            return {'success': False, 'error': 'Diagnóstico no encontrado'}
        except ValidationError as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def actualizar_tipo_cie_individual(
        diagnostico_cie_id: str,
        nuevo_tipo_cie: str,
        usuario
    ) -> Dict[str, Any]:
        """
        Actualiza el tipo CIE (PRE/DEF) de un diagnóstico individual
        """
        try:
            diagnostico = DiagnosticoCIEHistorial.objects.get(
                id=diagnostico_cie_id,
                activo=True
            )

            if diagnostico.historial_clinico.estado == 'CERRADO':
                raise ValidationError(
                    'No se pueden modificar diagnósticos de un historial cerrado'
                )

            if nuevo_tipo_cie not in [c[0] for c in DiagnosticoCIEHistorial.TipoCIE.choices]:
                raise ValidationError(f"Tipo CIE inválido: {nuevo_tipo_cie}")

            diagnostico.tipo_cie = nuevo_tipo_cie
            diagnostico.actualizado_por = usuario
            diagnostico.save()

            logger.info(
                f"Diagnóstico CIE {diagnostico_cie_id} actualizado a "
                f"tipo {nuevo_tipo_cie} por {usuario.username}"
            )

            return {
                'success': True,
                'message': 'Tipo CIE actualizado exitosamente',
                'diagnostico_id': str(diagnostico_cie_id),
                'tipo_cie': nuevo_tipo_cie,
                'tipo_cie_display': diagnostico.get_tipo_cie_display()
            }

        except DiagnosticoCIEHistorial.DoesNotExist:
            return {'success': False, 'error': 'Diagnóstico no encontrado'}
        except ValidationError as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def sincronizar_diagnosticos_historial(
        historial_id: str,
        diagnosticos_finales: List[Dict[str, Any]],
        tipo_carga: str,
        usuario
    ) -> Dict[str, Any]:
        """
        Sincroniza los diagnósticos CIE de un historial (mantiene solo los especificados).
        Ahora persiste codigo_cie_personalizado cuando el historial está en BORRADOR.
        """
        try:
            historial = ClinicalRecord.objects.get(id=historial_id, activo=True)

            if historial.estado == 'CERRADO':
                raise ValidationError('No se pueden modificar diagnósticos de un historial cerrado')

            # Solo BORRADOR permite personalizar códigos
            puede_personalizar = historial.estado == 'BORRADOR'

            diagnosticos_finales_ids = [
                str(diag['diagnostico_dental_id']) for diag in diagnosticos_finales
            ]

            # 1. Desactivar diagnósticos que no están en la lista final
            diagnosticos_actuales = DiagnosticoCIEHistorial.objects.filter(
                historial_clinico=historial,
                activo=True
            )

            desactivados = 0
            for diag_actual in diagnosticos_actuales:
                if str(diag_actual.diagnostico_dental_id) not in diagnosticos_finales_ids:
                    diag_actual.activo = False
                    diag_actual.actualizado_por = usuario
                    diag_actual.save()
                    desactivados += 1

            # 2. Activar/Crear diagnósticos que están en la lista final
            creados = 0
            actualizados = 0

            for diag_data in diagnosticos_finales:
                diagnostico_dental_id = diag_data['diagnostico_dental_id']
                tipo_cie = diag_data['tipo_cie']
                # NUEVO: código personalizado opcional
                codigo_personalizado = diag_data.get('codigo_cie_personalizado', None)

                try:
                    diagnostico_dental = DiagnosticoDental.objects.get(
                        id=diagnostico_dental_id,
                        activo=True
                    )

                    if not diagnostico_dental.diagnostico_catalogo or not diagnostico_dental.diagnostico_catalogo.codigo_icd10:
                        logger.warning(f"Diagnóstico {diagnostico_dental_id} no tiene código CIE, saltando")
                        continue

                    diag_existente = DiagnosticoCIEHistorial.objects.filter(
                        historial_clinico=historial,
                        diagnostico_dental=diagnostico_dental
                    ).first()

                    if diag_existente:
                        diag_existente.tipo_cie = tipo_cie
                        diag_existente.activo = True
                        diag_existente.actualizado_por = usuario
                        # NUEVO: actualizar código personalizado solo en BORRADOR
                        if puede_personalizar:
                            if codigo_personalizado and codigo_personalizado.strip():
                                diag_existente.codigo_cie_personalizado = codigo_personalizado.strip().upper()
                            elif codigo_personalizado == '':
                                # Cadena vacía explícita → restaurar catálogo
                                diag_existente.codigo_cie_personalizado = None
                        diag_existente.save()
                        actualizados += 1
                    else:
                        # NUEVO: incluir codigo_cie_personalizado al crear
                        crear_kwargs = {
                            'historial_clinico': historial,
                            'diagnostico_dental': diagnostico_dental,
                            'tipo_cie': tipo_cie,
                            'creado_por': usuario,
                            'activo': True,
                        }
                        if puede_personalizar and codigo_personalizado and codigo_personalizado.strip():
                            crear_kwargs['codigo_cie_personalizado'] = codigo_personalizado.strip().upper()

                        DiagnosticoCIEHistorial.objects.create(**crear_kwargs)
                        creados += 1

                except DiagnosticoDental.DoesNotExist:
                    logger.warning(f"Diagnóstico dental {diagnostico_dental_id} no encontrado")
                    continue

            # 3. Actualizar tracking en el historial
            historial.tipo_carga_diagnosticos = tipo_carga
            historial.diagnosticos_cie_cargados = len(diagnosticos_finales) > 0
            historial.save()

            logger.info(
                f"Sincronización completada para historial {historial_id}: "
                f"desactivados={desactivados}, creados={creados}, actualizados={actualizados}"
            )

            diagnosticos_actualizados = DiagnosticosCIEService.obtener_diagnosticos_historial(historial_id)

            return {
                'success': True,
                'message': 'Diagnósticos sincronizados exitosamente',
                'tipo_carga': tipo_carga,
                'total_diagnosticos': len(diagnosticos_actualizados),
                'estadisticas': {
                    'desactivados': desactivados,
                    'creados': creados,
                    'actualizados': actualizados,
                },
                'diagnosticos': diagnosticos_actualizados,
            }

        except ClinicalRecord.DoesNotExist:
            return {'success': False, 'error': 'Historial clínico no encontrado'}
        except ValidationError as e:
            return {'success': False, 'error': str(e)}