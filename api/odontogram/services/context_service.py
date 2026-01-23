# api/odontogram/services/context_service.py
"""
Servicio para manejar el contexto de operaciones y evitar snapshots duplicados
"""

import threading
from django.utils import timezone

class OperacionContexto:
    """
    Maneja el contexto de operaciones para evitar snapshots innecesarios.
    Thread-safe para entornos multi-hilo.
    """
    
    _lock = threading.RLock()
    _operaciones_activas = {}
    
    @classmethod
    def iniciar_operacion(cls, paciente_id: str, tipo: str = 'guardado_odontograma'):
        """
        Marca que una operación está en progreso.
        
        Args:
            paciente_id: ID del paciente
            tipo: Tipo de operación (default: 'guardado_odontograma')
        """
        with cls._lock:
            key = f"{paciente_id}:{tipo}"
            cls._operaciones_activas[key] = {
                'inicio': timezone.now(),
                'tipo': tipo,
                'paciente_id': paciente_id
            }
            print(f"[CONTEXTO] Operación iniciada: {key}")
    
    @classmethod
    def finalizar_operacion(cls, paciente_id: str, tipo: str = 'guardado_odontograma'):
        """
        Marca que una operación ha terminado.
        
        Args:
            paciente_id: ID del paciente
            tipo: Tipo de operación (default: 'guardado_odontograma')
        """
        with cls._lock:
            key = f"{paciente_id}:{tipo}"
            if key in cls._operaciones_activas:
                del cls._operaciones_activas[key]
                print(f"[CONTEXTO] Operación finalizada: {key}")
    
    @classmethod
    def esta_en_operacion(cls, paciente_id: str, tipo: str = None) -> bool:
        """
        Verifica si hay una operación en progreso.
        
        Args:
            paciente_id: ID del paciente
            tipo: Tipo específico de operación (si None, verifica cualquier tipo)
            
        Returns:
            True si hay una operación activa, False en caso contrario
        """
        with cls._lock:
            if tipo:
                key = f"{paciente_id}:{tipo}"
                return key in cls._operaciones_activas
            
            # Verificar cualquier operación para este paciente
            for key in cls._operaciones_activas.keys():
                if key.startswith(f"{paciente_id}:"):
                    return True
            return False
    
    @classmethod
    def limpiar_operaciones_antiguas(cls, minutos_max: int = 30):
        """
        Limpia operaciones que han estado activas por demasiado tiempo.
        Útil para prevenir memory leaks si una operación nunca se finalizó.
        
        Args:
            minutos_max: Tiempo máximo en minutos (default: 30)
        """
        with cls._lock:
            now = timezone.now()
            keys_a_eliminar = []
            
            for key, datos in cls._operaciones_activas.items():
                tiempo_transcurrido = (now - datos['inicio']).total_seconds() / 60
                if tiempo_transcurrido > minutos_max:
                    keys_a_eliminar.append(key)
            
            for key in keys_a_eliminar:
                del cls._operaciones_activas[key]
                print(f"[CONTEXTO] Limpiada operación antigua: {key}")


# Alias corto para uso frecuente
ContextoOperacion = OperacionContexto