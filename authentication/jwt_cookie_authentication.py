"""
============================================================================
JWT COOKIE AUTHENTICATION - Lee tokens de cookies
============================================================================
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from django.conf import settings


class JWTCookieAuthentication(JWTAuthentication):
    """
    Autenticación JWT que lee el token de las cookies
    Fallback a header Authorization si no hay cookie
    """
    
    def authenticate(self, request):
        # ✅ Primero intentar leer de cookie
        cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE', 'access_token')
        raw_token = request.COOKIES.get(cookie_name)
        
        # Si no hay cookie, intentar con header
        if raw_token is None:
            header = self.get_header(request)
            if header is None:
                return None
            
            raw_token = self.get_raw_token(header)
        
        if raw_token is None:
            return None

        # Validar token
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
