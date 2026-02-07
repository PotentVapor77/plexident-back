# api/parameters/services/seguridad_service.py
import re
import logging
from datetime import datetime, timedelta
from django.core.cache import cache
from ..repositories.parametro_repository import ParametroRepository
from api.users.models import Usuario

logger = logging.getLogger(__name__)


class SeguridadService:
    """Servicio para lógica de seguridad y validación de contraseñas"""
    
    @staticmethod
    def validar_complejidad_password(password: str, config=None) -> dict:
        """
        Validar contraseña según reglas de complejidad configuradas (RF-07.5)
        
        Args:
            password: Contraseña a validar
            config: ConfiguracionSeguridad object (si None, obtiene del repo)
        
        Returns:
            Dict con resultados de validación
        """
        if not config:
            config = ParametroRepository.get_configuracion_seguridad()
        
        errores = []
        
        # 1. Longitud mínima
        if len(password) < config.longitud_minima_password:
            errores.append(f"La contraseña debe tener al menos {config.longitud_minima_password} caracteres")
        
        # 2. Requerir mayúsculas
        if config.requiere_mayusculas and not re.search(r'[A-Z]', password):
            errores.append("La contraseña debe contener al menos una letra mayúscula")
        
        # 3. Requerir números
        if config.requiere_numeros and not re.search(r'\d', password):
            errores.append("La contraseña debe contener al menos un número")
        
        # 4. Requerir caracteres especiales
        if config.requiere_especiales and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errores.append("La contraseña debe contener al menos un carácter especial")
        
        # 5. Validaciones adicionales de seguridad
        if re.search(r'(.)\1{2,}', password):  # No más de 2 caracteres repetidos consecutivos
            errores.append("La contraseña no puede tener más de 2 caracteres idénticos consecutivos")
        
        if password.lower() in ['password', '123456', 'admin', 'contraseña']:
            errores.append("La contraseña es demasiado común o insegura")
        
        # 6. Verificar si es similar al username o email del usuario actual
        # (Esto se haría en el contexto de un usuario específico)
        
        es_valida = len(errores) == 0
        
        return {
            'es_valida': es_valida,
            'errores': errores,
            'fortaleza': SeguridadService._calcular_fortaleza_password(password, config)
        }
    
    @staticmethod
    def _calcular_fortaleza_password(password: str, config) -> str:
        """
        Calcular fortaleza de la contraseña (baja, media, alta, muy alta)
        
        Returns:
            String con nivel de fortaleza
        """
        puntaje = 0
        
        # Longitud
        if len(password) >= 12:
            puntaje += 2
        elif len(password) >= 8:
            puntaje += 1
        
        # Diversidad de caracteres
        if re.search(r'[a-z]', password):
            puntaje += 1
        if re.search(r'[A-Z]', password):
            puntaje += 1
        if re.search(r'\d', password):
            puntaje += 1
        if re.search(r'[^a-zA-Z0-9]', password):
            puntaje += 2
        
        # Determinar fortaleza
        if puntaje >= 6:
            return 'MUY_ALTA'
        elif puntaje >= 4:
            return 'ALTA'
        elif puntaje >= 2:
            return 'MEDIA'
        else:
            return 'BAJA'
    
    @staticmethod
    def registrar_intento_login_fallido(username: str, ip_address: str):
        """
        Registrar intento de login fallido y verificar si debe bloquearse
        
        Args:
            username: Username que intentó login
            ip_address: Dirección IP del intento
        
        Returns:
            Tuple (debe_bloquear, tiempo_restante_segundos)
        """
        cache_key_user = f'login_fallidos_user_{username}'
        cache_key_ip = f'login_fallidos_ip_{ip_address}'
        
        # Incrementar contadores
        intentos_user = cache.get(cache_key_user, 0) + 1
        intentos_ip = cache.get(cache_key_ip, 0) + 1
        
        # Obtener configuración
        config = ParametroRepository.get_configuracion_seguridad()
        
        # Guardar en cache (expiración según configuración)
        cache.set(cache_key_user, intentos_user, config.duracion_bloqueo_minutos * 60)
        cache.set(cache_key_ip, intentos_ip, config.duracion_bloqueo_minutos * 60)
        
        logger.warning(
            f"Intento de login fallido: usuario={username}, "
            f"IP={ip_address}, intentos_user={intentos_user}, intentos_ip={intentos_ip}"
        )
        
        # Verificar si excede límites
        if intentos_user >= config.max_intentos_login or intentos_ip >= config.max_intentos_login * 2:
            # Calcular tiempo restante de bloqueo
            tiempo_restante = cache.ttl(cache_key_user)
            return True, tiempo_restante
        
        return False, 0
    
    @staticmethod
    def resetear_intentos_login(username: str, ip_address: str = None):
        """Resetear contadores de intentos fallidos después de login exitoso"""
        cache_key_user = f'login_fallidos_user_{username}'
        cache.delete(cache_key_user)
        
        if ip_address:
            cache_key_ip = f'login_fallidos_ip_{ip_address}'
            cache.delete(cache_key_ip)
        
        logger.info(f"Intentos de login reseteados para usuario: {username}")
    
    @staticmethod
    def verificar_bloqueo_usuario(username: str) -> tuple[bool, int]:
        """
        Verificar si un usuario está bloqueado por intentos fallidos
        
        Returns:
            Tuple (esta_bloqueado, segundos_restantes)
        """
        cache_key = f'login_fallidos_user_{username}'
        intentos = cache.get(cache_key, 0)
        
        if intentos == 0:
            return False, 0
        
        config = ParametroRepository.get_configuracion_seguridad()
        
        if intentos >= config.max_intentos_login:
            tiempo_restante = cache.ttl(cache_key)
            return True, tiempo_restante
        
        return False, 0
    
    @staticmethod
    def obtener_politicas_seguridad() -> dict:
        """Obtener políticas de seguridad actuales para mostrar al usuario"""
        config = ParametroRepository.get_configuracion_seguridad()
        
        return {
            'longitud_minima': config.longitud_minima_password,
            'requiere_mayusculas': config.requiere_mayusculas,
            'requiere_numeros': config.requiere_numeros,
            'requiere_especiales': config.requiere_especiales,
            'historial_password_cantidad': config.historial_password_cantidad,
            'dias_validez_password': config.dias_validez_password,
            'tiempo_inactividad_minutos': config.tiempo_inactividad_minutos,
            'max_intentos_login': config.max_intentos_login,
            'duracion_bloqueo_minutos': config.duracion_bloqueo_minutos
        }
    
    @staticmethod
    def verificar_expiracion_password(usuario: Usuario) -> tuple[bool, int]:
        """
        Verificar si la contraseña del usuario ha expirado
        
        Args:
            usuario: Usuario a verificar
        
        Returns:
            Tuple (ha_expirado, dias_restantes)
        """
        if not usuario.last_login:
            return False, 0
        
        config = ParametroRepository.get_configuracion_seguridad()
        
        # Calcular fecha de expiración
        fecha_expiracion = usuario.last_login + timedelta(days=config.dias_validez_password)
        hoy = datetime.now().date()
        
        if hoy >= fecha_expiracion.date():
            return True, 0
        
        dias_restantes = (fecha_expiracion.date() - hoy).days
        return False, dias_restantes
    
    @staticmethod
    def verificar_historial_password(usuario: Usuario, nueva_password: str) -> bool:
        """
        Verificar si la nueva contraseña ha sido usada recientemente
        
        Args:
            usuario: Usuario
            nueva_password: Nueva contraseña a verificar
        
        Returns:
            True si la contraseña NO está en el historial reciente
        """
        # TODO: Implementar cuando se tenga el historial de contraseñas
        # Por ahora, siempre retorna True
        return True