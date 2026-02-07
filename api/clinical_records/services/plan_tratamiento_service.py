import logging
from api.odontogram.models import PlanTratamiento


logger = logging.getLogger(__name__)


class PlanTratamientoLinkService:
    """
    Servicio para gestionar la vinculación entre Plan de Tratamiento y Historial Clínico
    """
    
    @staticmethod
    def obtener_plan_activo_paciente(paciente_id):
        """
        Obtiene el plan de tratamiento activo más reciente del paciente
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            PlanTratamiento o None
        """
        try:
            return PlanTratamiento.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).select_related(
                'paciente',
                'creado_por'
            ).prefetch_related(
                'sesiones'
            ).order_by('-fecha_creacion').first()
        except Exception as e:
            logger.error(f"Error obteniendo plan activo para paciente {paciente_id}: {str(e)}")
            return None
    
    @staticmethod
    def obtener_plan_con_sesiones(plan_id):
        """
        Obtiene un plan específico con todas sus sesiones cargadas
        
        Args:
            plan_id: UUID del plan
            
        Returns:
            PlanTratamiento o None
        """
        try:
            return PlanTratamiento.objects.filter(
                id=plan_id,
                activo=True
            ).select_related(
                'paciente',
                'creado_por'
            ).prefetch_related(
                'sesiones__odontologo'
            ).first()
        except Exception as e:
            logger.error(f"Error obteniendo plan {plan_id}: {str(e)}")
            return None
    
    @staticmethod
    def vincular_plan_a_historial(historial, plan=None, paciente_id=None):
        """
        Vincula un plan de tratamiento a un historial clínico
        Si no se proporciona plan, busca el plan activo del paciente
        
        Args:
            historial: Instancia de ClinicalRecord
            plan: PlanTratamiento opcional
            paciente_id: UUID del paciente (usado si plan es None)
            
        Returns:
            bool: True si se vinculó exitosamente
        """
        try:
            if not plan and paciente_id:
                plan = PlanTratamientoLinkService.obtener_plan_activo_paciente(paciente_id)
            
            if plan:
                historial.plan_tratamiento = plan
                historial.save()
                logger.info(
                    f"Plan {plan.id} vinculado al historial {historial.id}"
                )
                return True
            else:
                logger.warning(
                    f"No se encontró plan activo para vincular al historial {historial.id}"
                )
                return False
                
        except Exception as e:
            logger.error(
                f"Error vinculando plan al historial {historial.id}: {str(e)}"
            )
            return False
    
    @staticmethod
    def obtener_todos_planes_paciente(paciente_id):
        """
        Obtiene todos los planes de tratamiento de un paciente
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            QuerySet de PlanTratamiento
        """
        try:
            return PlanTratamiento.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).select_related(
                'paciente',
                'creado_por'
            ).prefetch_related(
                'sesiones'
            ).order_by('-fecha_creacion')
        except Exception as e:
            logger.error(
                f"Error obteniendo planes para paciente {paciente_id}: {str(e)}"
            )
            return PlanTratamiento.objects.none()