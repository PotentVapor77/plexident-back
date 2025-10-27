# odontogram/services/odontogram_services.py
"""
Servicios para la nueva estructura de Odontograma
Maneja: Paciente -> Diente -> Superficie -> DiagnosticoDental
"""

from typing import List, Dict, Any, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model

from odontogram.models import (
    Paciente,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma,
    Diagnostico,
)

User = get_user_model()


class OdontogramaService:
    """
    Servicio para gestionar odontogramas de pacientes
    Conecta el frontend con la nueva estructura de BD
    """

    @transaction.atomic
    def guardar_odontograma_completo(
        self,
        paciente_id: str,
        odontologo_id: int,
        odontograma_data: Dict[str, Dict[str, List[Dict[str, Any]]]]
    ) -> Dict[str, Any]:
        """
        Guarda un odontograma completo del frontend

        Formato del frontend:
        {
            "11": {  # codigo_fdi (diente)
                "vestibular": [  # superficie
                    {
                        "procedimientoId": "caries_icdas_3",
                        "colorHex": "#FF5733",
                        "secondaryOptions": {"material": "resina"},
                        "descripcion": "Caries profunda",
                        "afectaArea": ["corona"]
                    }
                ]
            }
        }
        """
        try:
            paciente = Paciente.objects.get(id=paciente_id)
            odontologo = User.objects.get(id=odontologo_id)
        except (Paciente.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Paciente u odontólogo no encontrado")

        resultado = {
            'paciente_id': str(paciente.id),
            'dientes_procesados': [],
            'diagnosticos_guardados': 0,
            'errores': []
        }

        # Procesar cada diente
        for codigo_fdi, superficies_dict in odontograma_data.items():
            try:
                diente, created = Diente.objects.get_or_create(
                    paciente=paciente,
                    codigo_fdi=codigo_fdi
                )

                resultado['dientes_procesados'].append(codigo_fdi)

                # Procesar cada superficie
                for nombre_superficie, diagnosticos_list in superficies_dict.items():
                    try:
                        superficie, _ = SuperficieDental.objects.get_or_create(
                            diente=diente,
                            nombre=nombre_superficie
                        )

                        # Procesar cada diagnóstico
                        for diag_data in diagnosticos_list:
                            try:
                                # Buscar diagnóstico en catálogo
                                diagnostico_cat = Diagnostico.objects.get(
                                    key=diag_data['procedimientoId'],
                                    activo=True
                                )

                                # Crear diagnóstico dental (instancia)
                                diag_dental = DiagnosticoDental.objects.create(
                                    superficie=superficie,
                                    diagnostico_catalogo=diagnostico_cat,
                                    odontologo=odontologo,
                                    descripcion=diag_data.get('descripcion', ''),
                                    atributos_clinicos=diag_data.get('secondaryOptions', {}),
                                    estado_tratamiento=DiagnosticoDental.EstadoTratamiento.DIAGNOSTICADO
                                )

                                # Crear entrada de historial
                                HistorialOdontograma.objects.create(
                                    diente=diente,
                                    tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_AGREGADO,
                                    descripcion=f"Diagnóstico {diagnostico_cat.nombre} agregado en {superficie.get_nombre_display()}",
                                    odontologo=odontologo,
                                    datos_nuevos={
                                        'diagnostico': diagnostico_cat.key,
                                        'superficie': nombre_superficie,
                                        'atributos': diag_data.get('secondaryOptions', {})
                                    }
                                )

                                resultado['diagnosticos_guardados'] += 1

                            except Diagnostico.DoesNotExist:
                                resultado['errores'].append(
                                    f"Diagnóstico {diag_data.get('procedimientoId')} no encontrado"
                                )
                            except Exception as e:
                                resultado['errores'].append(
                                    f"Error guardando diagnóstico en {codigo_fdi}/{nombre_superficie}: {str(e)}"
                                )

                    except Exception as e:
                        resultado['errores'].append(
                            f"Error procesando superficie {nombre_superficie}: {str(e)}"
                        )

            except Exception as e:
                resultado['errores'].append(
                    f"Error procesando diente {codigo_fdi}: {str(e)}"
                )

        return resultado

    def obtener_odontograma_completo(self, paciente_id: str) -> Dict[str, Any]:
        """
        Obtiene el odontograma completo de un paciente
        en el formato esperado por el frontend
        """
        try:
            paciente = Paciente.objects.get(id=paciente_id)
        except Paciente.DoesNotExist:
            raise ValidationError("Paciente no encontrado")

        odontograma_data = {}

        # Obtener todos los dientes del paciente
        dientes = Diente.objects.filter(paciente=paciente).prefetch_related(
            'superficies__diagnosticos'
        )

        for diente in dientes:
            codigo_fdi = diente.codigo_fdi
            odontograma_data[codigo_fdi] = {}

            # Obtener superficies del diente
            for superficie in diente.superficies.all():
                odontograma_data[codigo_fdi][superficie.nombre] = []

                # Obtener diagnósticos de la superficie
                for diag_dental in superficie.diagnosticos.filter(activo=True):
                    odontograma_data[codigo_fdi][superficie.nombre].append({
                        'id': str(diag_dental.id),
                        'procedimientoId': diag_dental.diagnostico_catalogo.key,
                        'colorHex': diag_dental.diagnostico_catalogo.simbolo_color,
                        'secondaryOptions': diag_dental.atributos_clinicos,
                        'descripcion': diag_dental.descripcion,
                        'afectaArea': list(
                            diag_dental.diagnostico_catalogo.areas_relacionadas.values_list(
                                'area__key', flat=True
                            )
                        ),
                        'estado_tratamiento': diag_dental.estado_tratamiento,
                        'prioridad': diag_dental.prioridad_efectiva,
                        'fecha': diag_dental.fecha.isoformat(),
                        'odontologo': diag_dental.odontologo.get_full_name(),
                    })

        return {
            'paciente_id': str(paciente.id),
            'paciente_nombre': paciente.nombre_completo,
            'odontograma_data': odontograma_data,
            'fecha_obtension': timezone.now().isoformat(),
        }

    @transaction.atomic
    def marcar_diente_ausente(
        self,
        paciente_id: str,
        codigo_fdi: str,
        odontologo_id: int
    ) -> Diente:
        """
        Marca un diente como ausente y registra en historial
        """
        try:
            paciente = Paciente.objects.get(id=paciente_id)
            odontologo = User.objects.get(id=odontologo_id)
        except (Paciente.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Paciente u odontólogo no encontrado")

        diente, _ = Diente.objects.get_or_create(
            paciente=paciente,
            codigo_fdi=codigo_fdi
        )

        # Cambiar estado
        era_ausente = diente.ausente
        diente.ausente = True
        diente.save()

        # Crear historial
        if not era_ausente:
            HistorialOdontograma.objects.create(
                diente=diente,
                tipo_cambio=HistorialOdontograma.TipoCambio.DIENTE_MARCADO_AUSENTE,
                descripcion=f"Diente {codigo_fdi} marcado como ausente",
                odontologo=odontologo,
                datos_nuevos={'ausente': True}
            )

        return diente

    @transaction.atomic
    def eliminar_diagnostico(
        self,
        diagnostico_id: str,
        odontologo_id: int
    ) -> bool:
        """
        Elimina un diagnóstico (soft delete) y registra en historial
        """
        try:
            diagnostico = DiagnosticoDental.objects.get(id=diagnostico_id)
            odontologo = User.objects.get(id=odontologo_id)
        except (DiagnosticoDental.DoesNotExist, User.DoesNotExist):
            return False

        # Soft delete
        diagnostico.activo = False
        diagnostico.save()

        # Crear historial
        HistorialOdontograma.objects.create(
            diente=diagnostico.diente,
            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_ELIMINADO,
            descripcion=f"Diagnóstico {diagnostico.diagnostico_catalogo.nombre} eliminado de {diagnostico.superficie.get_nombre_display()}",
            odontologo=odontologo,
            datos_anteriores={
                'diagnostico': diagnostico.diagnostico_catalogo.key,
                'superficie': diagnostico.superficie.nombre,
            }
        )

        return True

    @transaction.atomic
    def actualizar_diagnostico(
        self,
        diagnostico_id: str,
        descripcion: Optional[str] = None,
        atributos_clinicos: Optional[Dict] = None,
        estado_tratamiento: Optional[str] = None,
        prioridad_asignada: Optional[int] = None,
        odontologo_id: Optional[int] = None
    ) -> Optional[DiagnosticoDental]:
        """
        Actualiza un diagnóstico y registra cambios en historial
        """
        try:
            diagnostico = DiagnosticoDental.objects.get(id=diagnostico_id)
            if odontologo_id:
                odontologo = User.objects.get(id=odontologo_id)
            else:
                odontologo = diagnostico.odontologo
        except (DiagnosticoDental.DoesNotExist, User.DoesNotExist):
            return None

        # Guardar datos anteriores para historial
        datos_anteriores = {
            'descripcion': diagnostico.descripcion,
            'atributos_clinicos': diagnostico.atributos_clinicos,
            'estado_tratamiento': diagnostico.estado_tratamiento,
            'prioridad_asignada': diagnostico.prioridad_asignada,
        }

        # Actualizar campos
        if descripcion is not None:
            diagnostico.descripcion = descripcion
        if atributos_clinicos is not None:
            diagnostico.atributos_clinicos = atributos_clinicos
        if estado_tratamiento is not None:
            diagnostico.estado_tratamiento = estado_tratamiento
        if prioridad_asignada is not None:
            if not 1 <= prioridad_asignada <= 5:
                raise ValidationError("Prioridad debe estar entre 1 y 5")
            diagnostico.prioridad_asignada = prioridad_asignada

        diagnostico.save()

        # Crear historial de cambios
        datos_nuevos = {
            'descripcion': diagnostico.descripcion,
            'atributos_clinicos': diagnostico.atributos_clinicos,
            'estado_tratamiento': diagnostico.estado_tratamiento,
            'prioridad_asignada': diagnostico.prioridad_asignada,
        }

        HistorialOdontograma.objects.create(
            diente=diagnostico.diente,
            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO,
            descripcion=f"Diagnóstico {diagnostico.diagnostico_catalogo.nombre} modificado",
            odontologo=odontologo,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        return diagnostico

    def obtener_historial_diente(self, codigo_fdi: str, paciente_id: str) -> List[HistorialOdontograma]:
        """
        Obtiene el historial de cambios de un diente específico
        """
        try:
            diente = Diente.objects.get(paciente_id=paciente_id, codigo_fdi=codigo_fdi)
            return list(diente.historial.all())
        except Diente.DoesNotExist:
            return []

    def obtener_diagnosticos_paciente(
        self,
        paciente_id: str,
        estado_tratamiento: Optional[str] = None
    ) -> List[DiagnosticoDental]:
        """
        Obtiene todos los diagnósticos de un paciente
        opcionalmente filtrados por estado
        """
        try:
            paciente = Paciente.objects.get(id=paciente_id)
        except Paciente.DoesNotExist:
            return []

        # Obtener todos los diagnósticos del paciente
        diagnosticos = DiagnosticoDental.objects.filter(
            superficie__diente__paciente=paciente,
            activo=True
        ).select_related(
            'diagnostico_catalogo',
            'superficie__diente',
            'odontologo'
        )

        if estado_tratamiento:
            diagnosticos = diagnosticos.filter(estado_tratamiento=estado_tratamiento)

        return list(diagnosticos)