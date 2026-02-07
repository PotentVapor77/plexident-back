from venv import logger
import logging
from api.odontogram.models import IndicadoresSaludBucal
from api.clinical_records.models.clinical_record import ClinicalRecord

logger = logging.getLogger(__name__)

class ClinicalRecordIndicadoresService:
    @staticmethod
    def obtener_indicadores_paciente(paciente_id):
        """
        Obtiene los últimos indicadores activos del paciente.
        Valida que contenga metadata de piezas usadas.
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            IndicadoresSaludBucal o None
        """
        try:
            indicador = IndicadoresSaludBucal.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).order_by('-fecha').first()
            
            # Validar metadata de piezas (advertencia si falta)
            if indicador and not indicador.piezas_usadas_en_registro:
                logger.warning(
                    f"Indicador {indicador.id} del paciente {paciente_id} no tiene "
                    f"piezas_usadas_en_registro. Podría ser un registro antiguo."
                )
            
            if indicador and not indicador.tiene_datos_completos:
                logger.warning(
                    f"Indicador {indicador.id} no tiene datos completos en al menos 3 piezas"
                )
            
            return indicador
            
        except Exception as e:
            logger.error(
                f"Error obteniendo indicadores del paciente {paciente_id}: {str(e)}",
                exc_info=True  
            )
            return None

    @staticmethod
    def recargar_indicadores_paciente(paciente_id: str):
        """
        Recarga indicadores CON información de contexto de suplentes
        """
        from api.odontogram.services.piezas_service import PiezasIndiceService
        
        # 1. Obtener últimos indicadores
        indicadores = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(paciente_id)
        if not indicadores:
            return None
        
        # 2. Obtener estado ACTUAL de piezas (puede haber cambiado)
        info_piezas_actual = PiezasIndiceService.obtener_informacion_piezas(str(paciente_id))
        
        # 3. Obtener estado de piezas DEL REGISTRO
        info_piezas_registro = indicadores.piezas_usadas_en_registro or {}
        
        # 4. Preparar datos con contexto completo
        datos_prellenado = {}
        advertencias = []
        
        piezas = ['16', '11', '26', '36', '31', '46']
        for pieza in piezas:
            # Valores del registro
            placa = getattr(indicadores, f'pieza_{pieza}_placa', None)
            calculo = getattr(indicadores, f'pieza_{pieza}_calculo', None)
            gingivitis = getattr(indicadores, f'pieza_{pieza}_gingivitis', None)
            
            if all(v is not None for v in [placa, calculo, gingivitis]):
                datos_prellenado[f'pieza_{pieza}_placa'] = placa
                datos_prellenado[f'pieza_{pieza}_calculo'] = calculo
                datos_prellenado[f'pieza_{pieza}_gingivitis'] = gingivitis
                
                # Información de suplente del registro
                mapeo_registro = info_piezas_registro.get('piezas_mapeo', {}).get(pieza, {})
                es_suplente_registro = mapeo_registro.get('es_alternativa', False)
                
                # Información actual de la pieza
                mapeo_actual = info_piezas_actual.get('piezas_mapeo', {}).get(pieza, {})
                es_suplente_actual = mapeo_actual.get('es_alternativa', False)
                
                # Generar advertencias
                if es_suplente_registro and not es_suplente_actual:
                    advertencias.append({
                        'tipo': 'cambio_disponibilidad',
                        'pieza': pieza,
                        'mensaje': f"La pieza {pieza} ahora está disponible. "
                                f"Valores anteriores fueron de la pieza {mapeo_registro.get('codigo_usado')}"
                    })
                elif es_suplente_registro:
                    advertencias.append({
                        'tipo': 'suplente_previo',
                        'pieza': pieza,
                        'mensaje': f"Valores de registro anterior usando pieza "
                                f"{mapeo_registro.get('codigo_usado')} como suplente"
                    })
        
        return {
            'valores': datos_prellenado,
            'metadata_registro': {
                'fecha_registro': indicadores.fecha,
                'denticion': info_piezas_registro.get('denticion'),
                'estadisticas_registro': info_piezas_registro.get('estadisticas')
            },
            'estado_actual_piezas': {
                'denticion': info_piezas_actual.get('denticion'),
                'estadisticas': info_piezas_actual.get('estadisticas'),
                'piezas_mapeo': info_piezas_actual.get('piezas_mapeo')
            },
            'advertencias': advertencias
        }

    @staticmethod
    def refrescar_en_historial(historial_id: str):
        """
        Fuerza la actualización de la referencia de indicadores 
        en el historial clínico.
        
        Args:
            historial_id: UUID del historial clínico
            
        Returns:
            IndicadoresSaludBucal o None
        """
        try:
            historial = ClinicalRecord.objects.get(id=historial_id)
            indicadores = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(
                str(historial.paciente_id)
            )
            
            if indicadores:
                logger.info(f"Indicadores refrescados para historial {historial_id}")
                return indicadores
            
            logger.warning(f"No se encontraron indicadores para historial {historial_id}")
            return None
            
        except ClinicalRecord.DoesNotExist:
            logger.error(f"Historial {historial_id} no encontrado")
            return None
        except Exception as e:
            logger.error(f"Error refrescando indicadores en historial {historial_id}: {str(e)}")
            return None
    
    @staticmethod
    def obtener_indicadores_historial(historial_id: str):
        """
        Obtiene los indicadores asociados a un historial clínico específico.
        
        Args:
            historial_id: UUID del historial clínico
            
        Returns:
            dict con datos serializados o None
        """
        from api.clinical_records.serializers.oral_health_indicators import (
            OralHealthIndicatorsSerializer
        )
        
        try:
            historial = ClinicalRecord.objects.get(id=historial_id)
            
            # Si el historial tiene indicadores asociados directamente
            if historial.indicadores_salud_bucal:
                indicador = historial.indicadores_salud_bucal
            else:
                # Buscar los últimos indicadores del paciente
                indicador = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(
                    str(historial.paciente_id)
                )
            
            if not indicador:
                logger.warning(f"No hay indicadores para el historial {historial_id}")
                return None
            
            # Serializar
            serializer = OralHealthIndicatorsSerializer(indicador)
            return serializer.data
            
        except ClinicalRecord.DoesNotExist:
            logger.error(f"Historial {historial_id} no encontrado")
            return None
        except Exception as e:
            logger.error(f"Error obteniendo indicadores del historial {historial_id}: {str(e)}")
            return None