# api/clinical_records/services/form033_storage_service.py
"""
Servicio para procesar y almacenar datos del Formulario 033
en el historial clínico
"""
import logging
from typing import Dict, Any, Optional
from django.core.exceptions import ValidationError

from api.clinical_records.models import Form033Snapshot
from api.odontogram.services.form033_service import Form033Service


logger = logging.getLogger(__name__)


class Form033StorageService:
    """
    Servicio para integrar datos del Form033 con historiales clínicos
    """
    
    @classmethod
    def crear_snapshot_desde_paciente(
        cls,
        historial_clinico,
        usuario,
        observaciones: str = ''
    ) -> Form033Snapshot:
        """
        Crea un snapshot del Form033 extrayendo datos actuales del paciente
        
        Args:
            historial_clinico: Instancia de ClinicalRecord
            usuario: Usuario que crea el snapshot
            observaciones: Observaciones opcionales
        
        Returns:
            Form033Snapshot creado
        """
        try:
            # Usar el servicio existente para generar datos
            form033_service = Form033Service()
            datos_form033 = form033_service.generar_datos_form033(
                str(historial_clinico.paciente.id)
            )
            
            # Crear snapshot
            snapshot = Form033Snapshot.objects.create(
                historial_clinico=historial_clinico,
                datos_form033=datos_form033,
                capturado_por=usuario,
                observaciones=observaciones
            )
            
            logger.info(
                f"Snapshot Form033 creado para historial "
                f"{historial_clinico.numero_historia_clinica_unica}"
            )
            
            return snapshot
            
        except Exception as e:
            logger.error(
                f"Error creando snapshot Form033: {str(e)}"
            )
            raise ValidationError(
                f"No se pudo crear el snapshot del odontograma: {str(e)}"
            )
    
    
    @classmethod
    def crear_snapshot_desde_datos(
        cls,
        historial_clinico,
        datos_form033: Dict[str, Any],
        usuario,
        observaciones: str = ''
    ) -> Form033Snapshot:
        """
        Crea un snapshot del Form033 usando datos proporcionados
        (útil cuando el frontend ya tiene los datos cargados)
        
        Args:
            historial_clinico: Instancia de ClinicalRecord
            datos_form033: Diccionario con datos del Form033
            usuario: Usuario que crea el snapshot
            observaciones: Observaciones opcionales
        
        Returns:
            Form033Snapshot creado
        """
        try:
            # Validar estructura básica
            cls._validar_estructura_form033(datos_form033)
            
            # Crear snapshot
            snapshot = Form033Snapshot.objects.create(
                historial_clinico=historial_clinico,
                datos_form033=datos_form033,
                capturado_por=usuario,
                observaciones=observaciones
            )
            
            logger.info(
                f"Snapshot Form033 creado desde datos proporcionados para historial "
                f"{historial_clinico.numero_historia_clinica_unica}"
            )
            
            return snapshot
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                f"Error creando snapshot Form033 desde datos: {str(e)}"
            )
            raise ValidationError(
                f"No se pudo crear el snapshot del odontograma: {str(e)}"
            )
    
    
    @classmethod
    def actualizar_snapshot(
        cls,
        snapshot_id,
        datos_form033: Optional[Dict[str, Any]] = None,
        observaciones: Optional[str] = None
    ) -> Form033Snapshot:
        """
        Actualiza un snapshot existente
        
        Args:
            snapshot_id: ID del snapshot
            datos_form033: Nuevos datos (opcional)
            observaciones: Nuevas observaciones (opcional)
        
        Returns:
            Form033Snapshot actualizado
        """
        try:
            snapshot = Form033Snapshot.objects.get(id=snapshot_id)
            
            if datos_form033 is not None:
                cls._validar_estructura_form033(datos_form033)
                snapshot.datos_form033 = datos_form033
            
            if observaciones is not None:
                snapshot.observaciones = observaciones
            
            snapshot.save()
            
            logger.info(f"Snapshot Form033 {snapshot_id} actualizado")
            
            return snapshot
            
        except Form033Snapshot.DoesNotExist:
            raise ValidationError(
                f"Snapshot con ID {snapshot_id} no encontrado"
            )
        except Exception as e:
            logger.error(
                f"Error actualizando snapshot Form033: {str(e)}"
            )
            raise ValidationError(
                f"No se pudo actualizar el snapshot: {str(e)}"
            )
    
    
    @classmethod
    def obtener_snapshot_por_historial(cls, historial_id) -> Optional[Form033Snapshot]:
        """
        Obtiene el snapshot asociado a un historial clínico
        
        Args:
            historial_id: ID del historial clínico
        
        Returns:
            Form033Snapshot o None si no existe
        """
        try:
            return Form033Snapshot.objects.select_related(
                'historial_clinico',
                'capturado_por'
            ).get(historial_clinico_id=historial_id, activo=True)
        except Form033Snapshot.DoesNotExist:
            return None
    
    
    @classmethod
    def eliminar_snapshot(cls, snapshot_id):
        """
        Eliminación lógica del snapshot
        
        Args:
            snapshot_id: ID del snapshot
        """
        try:
            snapshot = Form033Snapshot.objects.get(id=snapshot_id)
            snapshot.activo = False
            snapshot.save()
            
            logger.info(f"Snapshot Form033 {snapshot_id} eliminado (desactivado)")
            
        except Form033Snapshot.DoesNotExist:
            raise ValidationError(
                f"Snapshot con ID {snapshot_id} no encontrado"
            )
    
    
    @staticmethod
    def _validar_estructura_form033(datos: Dict[str, Any]):
        """
        Valida que los datos del Form033 tengan la estructura correcta
        
        Args:
            datos: Diccionario con datos del Form033
        
        Raises:
            ValidationError: Si la estructura es inválida
        """
        if not isinstance(datos, dict):
            raise ValidationError(
                'Los datos del Form033 deben ser un diccionario'
            )
        
        # Validar claves requeridas
        required_keys = ['odontograma_permanente', 'odontograma_temporal']
        for key in required_keys:
            if key not in datos:
                raise ValidationError(
                    f'Falta la clave requerida en Form033: {key}'
                )
        
        # Validar estructura de odontogramas
        for key in required_keys:
            odontograma = datos[key]
            if not isinstance(odontograma, dict):
                raise ValidationError(
                    f'{key} debe ser un diccionario'
                )
            
            if 'dientes' not in odontograma:
                raise ValidationError(
                    f'{key} debe contener la clave "dientes"'
                )
            
            if not isinstance(odontograma['dientes'], list):
                raise ValidationError(
                    f'{key}.dientes debe ser una lista'
                )
    
    
    @classmethod
    def generar_resumen_clinico(cls, snapshot: Form033Snapshot) -> str:
        """
        Genera un resumen clínico textual del snapshot para el historial
        
        Args:
            snapshot: Instancia de Form033Snapshot
        
        Returns:
            String con resumen clínico
        """
        stats = snapshot.resumen_estadistico
        
        resumen_parts = [
            "=== RESUMEN ODONTOLÓGICO ===",
            f"Total de dientes con diagnóstico: {stats['total_dientes_con_diagnostico']}",
            f"  - Permanentes: {stats['permanentes']}",
            f"  - Temporales: {stats['temporales']}",
            "",
            "Hallazgos principales:",
            f"  - Caries detectadas: {stats['caries']}",
            f"  - Dientes ausentes: {stats['ausentes']}",
            f"  - Dientes obturados: {stats['obturados']}",
        ]
        
        if snapshot.observaciones:
            resumen_parts.extend([
                "",
                "Observaciones:",
                snapshot.observaciones
            ])
        
        return "\n".join(resumen_parts)
