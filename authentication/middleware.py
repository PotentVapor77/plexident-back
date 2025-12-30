"""
============================================================================
AUTHENTICATION MIDDLEWARE
============================================================================
Middlewares personalizados para autenticación y seguridad
"""

from django.core.cache import cache
from django.http import JsonResponse
import json
import re


# ============================================================================
# CSRF EXEMPT MIDDLEWARE
# ============================================================================

class CSRFExemptMiddleware:
    """
    Middleware que exime ciertos endpoints de la verificación CSRF.
    
    Esto es necesario porque @csrf_exempt no funciona con @api_view de DRF.
    El middleware intercepta las requests ANTES de que Django verifique CSRF.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Patrones de URLs que NO requieren CSRF
        self.exempt_patterns = [
            r'^api/auth/login/?$',
            r'^api/auth/logout/?$',
            r'^api/auth/refresh/?$',
        ]
    
    def __call__(self, request):
        # Obtener path sin query string
        path = request.path_info.lstrip('/')
        
        # Verificar si el path coincide con alguna URL exenta
        for pattern in self.exempt_patterns:
            if re.match(pattern, path):
                # Marcar request como exenta de CSRF
                setattr(request, '_dont_enforce_csrf_checks', True)
                break
        
        response = self.get_response(request)
        return response


# ============================================================================
# LOGIN RATE LIMIT MIDDLEWARE
# ============================================================================

class LoginRateLimitMiddleware:
    """
    Middleware para limitar intentos de login por IP.
    Bloquea después de 5 intentos fallidos durante 1 minuto.
    
    Previene ataques de fuerza bruta en el endpoint de login.
    """
    MAX_ATTEMPTS = 5  # Máximo de intentos permitidos
    BLOCK_DURATION = 60  # Duración del bloqueo en segundos

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Solo aplicar a endpoint de login
        if request.path == '/api/auth/login/' and request.method == 'POST':
            ip = self.get_client_ip(request)
            cache_key = f'login_attempts_{ip}'

            # Obtener intentos actuales
            attempts = cache.get(cache_key, 0)

            # Si ya superó el límite, bloquear
            if attempts >= self.MAX_ATTEMPTS:
                return JsonResponse({
                    'success': False,
                    'error_type': 'TooManyRequests',
                    'message': f'Demasiados intentos. Espera {self.BLOCK_DURATION} segundos antes de volver a intentar.'
                }, status=429)

            # Incrementar contador
            cache.set(cache_key, attempts + 1, self.BLOCK_DURATION)

        # Procesar request normal
        response = self.get_response(request)

        # Si login fue exitoso, resetear contador
        if request.path == '/api/auth/login/' and request.method == 'POST':
            if response.status_code == 200:
                try:
                    data = json.loads(response.content)
                    if data.get('success'):
                        ip = self.get_client_ip(request)
                        cache_key = f'login_attempts_{ip}'
                        cache.delete(cache_key)  # Limpiar intentos fallidos
                except (json.JSONDecodeError, KeyError):
                    pass  # Si falla el parsing, ignorar

        return response

    def get_client_ip(self, request):
        """
        Obtiene la IP real del cliente, considerando proxies.
        """
        # Obtener IP desde header X-Forwarded-For (si hay proxy/nginx)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Tomar la primera IP (la del cliente real)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            # Si no hay proxy, tomar IP directa
            ip = request.META.get('REMOTE_ADDR')
        return ip

