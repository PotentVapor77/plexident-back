# api/clinical_records/services/examenes_complementarios_service.py
"""
Servicio para vincular Exámenes Complementarios al Historial Clínico.
Sigue el mismo patrón que PlanTratamientoLinkService e IndicadoresService.
"""
import logging
from typing import Optional

from api.patients.models.examenes_complementarios import ExamenesComplementarios

logger = logging.getLogger(__name__)


class ExamenesComplementariosLinkService:
    """
    Servicio para obtener y vincular exámenes complementarios
    al historial clínico.
    """

    @staticmethod
    def obtener_ultimo_examen_paciente(
        paciente_id,
    ) -> Optional[ExamenesComplementarios]:
        """
        Obtiene el último registro de exámenes complementarios activo
        del paciente para pre-cargar en el historial.

        Args:
            paciente_id: UUID del paciente

        Returns:
            ExamenesComplementarios o None
        """
        try:
            examen = (
                ExamenesComplementarios.objects.filter(
                    paciente_id=paciente_id,
                    activo=True,
                )
                .order_by('-fecha_creacion')
                .first()
            )

            if examen:
                logger.info(
                    f"Examen complementario {examen.id} encontrado "
                    f"para paciente {paciente_id}"
                )
            else:
                logger.info(
                    f"No hay exámenes complementarios previos "
                    f"para paciente {paciente_id}"
                )

            return examen

        except Exception as e:
            logger.error(
                f"Error obteniendo exámenes complementarios "
                f"para paciente {paciente_id}: {str(e)}"
            )
            return None

    @staticmethod
    def obtener_examenes_pendientes_paciente(paciente_id):
        """
        Obtiene exámenes con pedido pendiente (solicitados pero sin informe).

        Returns:
            QuerySet de ExamenesComplementarios pendientes
        """
        return ExamenesComplementarios.objects.filter(
            paciente_id=paciente_id,
            activo=True,
            pedido_examenes='SI',
            informe_examenes='NINGUNO',
        ).order_by('-fecha_creacion')

    @staticmethod
    def obtener_todos_examenes_paciente(paciente_id):
        """
        Obtiene todos los exámenes complementarios activos del paciente.

        Returns:
            QuerySet de ExamenesComplementarios
        """
        return ExamenesComplementarios.objects.filter(
            paciente_id=paciente_id,
            activo=True,
        ).order_by('-fecha_creacion')