# api/odontogram/services/odontogram_history_service.py
from typing import List, Dict, Any
from django.core.cache import cache
from api.odontogram.models import HistorialOdontograma, Diente

class OdontogramHistoryService:
    def registrar_cambio(self, diente, tipo_cambio, descripcion, odontologo, 
                        datos_anteriores=None, datos_nuevos=None, version_id=None):
        """Centraliza la creación de logs en el historial."""
        return HistorialOdontograma.objects.create(
            diente=diente,
            tipo_cambio=tipo_cambio,
            descripcion=descripcion,
            odontologo=odontologo,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            version_id=version_id
        )

    def obtener_historial_diente(self, codigo_fdi: str, paciente_id: str) -> List       [HistorialOdontograma]:
        """
        Obtiene el historial de cambios de un diente específico
        """
        try:
            diente = Diente.objects.get(paciente_id=paciente_id, codigo_fdi=codigo_fdi)
            return list(diente.historial.all())
        except Diente.DoesNotExist:
            return []
    def obtener_estado_version(self, version_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado completo del odontograma en una versión específica
        CON CACHÉ para reconstrucción rápida en frontend 3D
        """
        cache_key = f'odontograma:estado_version:{version_id}'
        estado = cache.get(cache_key)
        
        if not estado:
            # Obtener todos los cambios de esa versión
            cambios = HistorialOdontograma.objects.filter(
                version_id=version_id
            ).select_related(
                'diente',
                'odontologo'
            ).order_by('fecha', 'id')
            
            # Reconstruir estado del odontograma
            estado = {
                'version_id': str(version_id),
                'cambios': [],
                'diagnosticos_activos': {},
                'dientes_modificados': set()
            }
            
            for cambio in cambios:
                estado['cambios'].append({
                    'tipo': cambio.tipo_cambio,
                    'descripcion': cambio.descripcion,
                    'fecha': cambio.fecha.isoformat(),
                    'odontologo': cambio.odontologo.get_full_name(),
                    'datos_anteriores': cambio.datos_anteriores,
                    'datos_nuevos': cambio.datos_nuevos,
                })
                
                estado['dientes_modificados'].add(cambio.diente.codigo_fdi)
            
            # Convertir set a list para JSON
            estado['dientes_modificados'] = list(estado['dientes_modificados'])
            
            # Caché de 24 horas (versiones históricas no cambian)
            cache.set(cache_key, estado, timeout=86400)
        
        return estado