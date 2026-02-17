# api/clinical_records/services/odontograma_capture_service.py
"""
Servicio para gestionar la captura y almacenamiento de imágenes del odontograma.
"""
import logging
from typing import Optional, Dict, Any
from django.core.files.base import ContentFile
from django.db import transaction

from api.clinical_records.models import ClinicalRecord, Form033Snapshot

logger = logging.getLogger(__name__)


class OdontogramaCaptureService:
    """
    Servicio centralizado para manejar capturas de odontograma.
    """
    
    @staticmethod
    def guardar_imagen(
        historial: ClinicalRecord,
        imagen_file,
        observaciones: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guarda la imagen del odontograma en el snapshot asociado al historial.
        
        Args:
            historial: Instancia de ClinicalRecord
            imagen_file: Archivo de imagen (Django UploadedFile o ContentFile)
            observaciones: Notas opcionales sobre la captura
            
        Returns:
            Diccionario con el resultado de la operación
        """
        try:
            with transaction.atomic():
                # Obtener o crear snapshot
                snapshot, created = Form033Snapshot.objects.get_or_create(
                    historial_clinico=historial,
                    defaults={
                        'datos_form033': {
                            'odontograma_permanente': {
                                'dientes': [],
                                'movilidad': [],
                                'recesion': []
                            },
                            'odontograma_temporal': {
                                'dientes': [],
                                'movilidad': [],
                                'recesion': []
                            },
                        }
                    }
                )
                
                # Si ya tenía una imagen, eliminar el archivo anterior
                if snapshot.imagen_odontograma:
                    snapshot.imagen_odontograma.delete(save=False)
                
                # Guardar la nueva imagen
                snapshot.imagen_odontograma = imagen_file
                
                # Actualizar observaciones si se proporcionan
                if observaciones:
                    snapshot.observaciones = observaciones
                
                snapshot.save()
                
                logger.info(
                    f"Imagen de odontograma {'creada' if created else 'actualizada'} "
                    f"para historial {historial.id}"
                )
                
                return {
                    'success': True,
                    'created': created,
                    'snapshot_id': snapshot.id,
                    'fecha_captura': snapshot.fecha_captura,
                    'tiene_imagen': snapshot.tiene_imagen(),
                    'imagen_url': snapshot.get_imagen_url() if snapshot.tiene_imagen() else None
                }
                
        except Exception as e:
            logger.error(
                f"Error al guardar imagen de odontograma para historial {historial.id}: {e}",
                exc_info=True
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def eliminar_imagen(historial: ClinicalRecord) -> Dict[str, Any]:
        """
        Elimina la imagen del odontograma sin borrar los datos JSON.
        
        Args:
            historial: Instancia de ClinicalRecord
            
        Returns:
            Diccionario con el resultado de la operación
        """
        try:
            snapshot = Form033Snapshot.objects.filter(
                historial_clinico=historial
            ).first()
            
            if not snapshot:
                return {
                    'success': False,
                    'error': 'No existe snapshot para este historial'
                }
            
            if snapshot.imagen_odontograma:
                snapshot.imagen_odontograma.delete(save=False)
                snapshot.imagen_odontograma = None
                snapshot.save()
                
                logger.info(f"Imagen de odontograma eliminada para historial {historial.id}")
                
                return {
                    'success': True,
                    'message': 'Imagen eliminada correctamente'
                }
            else:
                return {
                    'success': False,
                    'error': 'No hay imagen asociada'
                }
                
        except Exception as e:
            logger.error(f"Error al eliminar imagen de odontograma: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def obtener_info_imagen(historial: ClinicalRecord) -> Dict[str, Any]:
        """
        Obtiene información sobre la imagen del odontograma.
        
        Args:
            historial: Instancia de ClinicalRecord
            
        Returns:
            Diccionario con información de la imagen
        """
        try:
            snapshot = Form033Snapshot.objects.filter(
                historial_clinico=historial
            ).first()
            
            if not snapshot:
                return {
                    'existe_snapshot': False,
                    'tiene_imagen': False
                }
            
            return {
                'existe_snapshot': True,
                'tiene_imagen': snapshot.tiene_imagen(),
                'fecha_captura': snapshot.fecha_captura,
                'imagen_url': snapshot.get_imagen_url() if snapshot.tiene_imagen() else None,
                'observaciones': snapshot.observaciones
            }
            
        except Exception as e:
            logger.error(f"Error al obtener info de imagen: {e}")
            return {
                'existe_snapshot': False,
                'tiene_imagen': False,
                'error': str(e)
            }