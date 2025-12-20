"""
============================================================================
AUTHENTICATION VIEWS
============================================================================
Endpoints de autenticación con JWT en HttpOnly cookies
"""

import json
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.conf import settings
from authentication.serializers import AuthUserSerializer, LoginSerializer
from api.users.models import Usuario

logger = logging.getLogger(__name__)


# ============================================================================
# RESPONSE HELPERS
# ============================================================================

def success_response(message, data=None, status_code=200):
    """Respuesta exitosa estandarizada"""
    response_data = {'success': True, 'message': message}
    if data:
        response_data['data'] = data
    return JsonResponse(response_data, status=status_code)


def error_response(status_code, error_type, message):
    """Respuesta de error estandarizada"""
    return JsonResponse({
        'success': False,
        'error_type': error_type,
        'message': message
    }, status=status_code)


def validation_error_response(serializer_errors, message):
    """Respuesta de error de validación"""
    return JsonResponse({
        'success': False,
        'message': message,
        'errors': serializer_errors
    }, status=400)


# ============================================================================
# COOKIE HELPER
# ============================================================================

def set_auth_cookie(response, key, value, max_age):
    """
    Configura cookie de autenticación según el entorno.
    
    En desarrollo: sin secure, sin domain (para localhost:puerto)
    En producción: con secure=True
    """
    cookie_params = {
        'key': key,
        'value': value,
        'httponly': True,
        'samesite': 'Lax',
        'max_age': max_age,
        'path': '/',
    }
    
    # Solo en producción agregar secure=True
    if not settings.DEBUG:
        cookie_params['secure'] = True
    
    response.set_cookie(**cookie_params)


# ============================================================================
# LOGIN
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Endpoint para login de usuarios.
    Retorna datos del usuario y guarda tokens en cookies HttpOnly.
    
    CSRF está deshabilitado por CSRFExemptMiddleware.
    """
    try:
        # Parsear request body
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body) if request.body else {}
            except json.JSONDecodeError:
                return error_response(400, "Bad Request", "JSON inválido")
        else:
            data = request.data

        # Validar datos de entrada
        serializer = LoginSerializer(data=data)
        if not serializer.is_valid():
            return validation_error_response(
                serializer.errors,
                "Error en los datos de login"
            )

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        # Autenticar usuario
        usuario = authenticate(request, username=username, password=password)

        if not usuario:
            return error_response(
                401,
                "Unauthorized",
                "Usuario o contraseña incorrectos"
            )

        if not usuario.is_active:
            return error_response(
                403,
                "Forbidden",
                "Cuenta desactivada"
            )

        # Generar tokens JWT
        refresh = RefreshToken.for_user(usuario)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Serializar datos del usuario
        user_data = AuthUserSerializer(usuario).data

        logger.info(f"✅ Login exitoso: {usuario.username}")

        # Crear respuesta con datos del usuario
        response = success_response(
            message="Login exitoso",
            data={'user': user_data}
        )

        # Guardar tokens en cookies
        set_auth_cookie(response, 'access_token', access_token, 3600)  # 1 hora
        set_auth_cookie(response, 'refresh_token', refresh_token, 604800)  # 7 días

        return response

    except Exception as e:
        logger.error(f"Error en login: {str(e)}", exc_info=True)
        return error_response(
            500,
            "Internal Server Error",
            "Error interno del servidor"
        )


# ============================================================================
# GET ME
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_me(request):
    """
    Obtener perfil del usuario actual autenticado.
    El token se lee automáticamente de las cookies por JWTCookieAuthentication.
    """
    try:
        usuario = request.user

        if not usuario or not usuario.is_authenticated:
            return error_response(401, "Unauthorized", "No autenticado")

        user_data = AuthUserSerializer(usuario).data

        return success_response(
            message="Usuario obtenido exitosamente",
            data={'user': user_data}
        )

    except Exception as e:
        logger.error(f"Error obteniendo usuario: {str(e)}", exc_info=True)
        return error_response(
            500,
            "Internal Server Error",
            "Error interno del servidor"
        )


# ============================================================================
# REFRESH TOKEN
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token_view(request):
    """
    Endpoint para refrescar tokens.
    
    Si ROTATE_REFRESH_TOKENS=True, genera nuevo refresh token.
    CSRF está deshabilitado por CSRFExemptMiddleware.
    """
    try:
        # Leer refresh token de cookies
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return error_response(
                401,
                "Unauthorized",
                "No hay refresh token disponible"
            )

        try:
            # Validar refresh token
            old_refresh = RefreshToken(refresh_token)
            
            # Obtener user_id del token
            user_id = old_refresh.payload.get('user_id')
            if not user_id:
                raise TokenError("Token no contiene user_id")

            # Obtener usuario
            try:
                usuario = Usuario.objects.get(id=user_id)
            except Usuario.DoesNotExist:
                return error_response(
                    401,
                    "Unauthorized",
                    "Usuario no encontrado"
                )

            # Verificar si rotation está habilitado
            simple_jwt_settings = getattr(settings, 'SIMPLE_JWT', {})
            rotate_refresh = simple_jwt_settings.get('ROTATE_REFRESH_TOKENS', False)
            blacklist_after = simple_jwt_settings.get('BLACKLIST_AFTER_ROTATION', False)

            logger.info(f"🔄 Refrescando token para: {usuario.username}")

            # Crear respuesta
            response = success_response(
                message="Token refrescado exitosamente",
                data={'refreshed': True}
            )

            if rotate_refresh:
                # Rotación de tokens habilitada
                if blacklist_after:
                    try:
                        old_refresh.blacklist()
                        logger.info(" ✅ Token antiguo blacklisteado")
                    except AttributeError:
                        logger.warning(" ⚠️ Blacklist no disponible")
                    except Exception as e:
                        logger.warning(f" ⚠️ Error al blacklistear: {str(e)}")

                # Generar nuevo refresh token
                new_refresh = RefreshToken.for_user(usuario)
                new_refresh_token = str(new_refresh)
                new_access_token = str(new_refresh.access_token)

                # Actualizar ambas cookies
                set_auth_cookie(response, 'access_token', new_access_token, 3600)
                set_auth_cookie(response, 'refresh_token', new_refresh_token, 604800)
            else:
                # Rotación deshabilitada - solo nuevo access token
                new_access_token = str(old_refresh.access_token)
                set_auth_cookie(response, 'access_token', new_access_token, 3600)

            logger.info(f"✅ Token refresh exitoso para: {usuario.username}")
            return response

        except TokenError as e:
            logger.warning(f"⚠️ Token inválido o expirado: {str(e)}")
            return error_response(
                401,
                "Unauthorized",
                "Refresh token inválido o expirado"
            )

    except Exception as e:
        logger.error(f"Error al refrescar token: {str(e)}", exc_info=True)
        return error_response(
            500,
            "Internal Server Error",
            "Error interno del servidor"
        )


# ============================================================================
# LOGOUT
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Endpoint para cerrar sesión.
    Elimina las cookies, blacklistea el refresh token y destruye la sesión Django.
    """
    try:
        # Leer refresh token de cookies
        refresh_token = request.COOKIES.get('refresh_token')

        if refresh_token:
            try:
                # Blacklist el refresh token
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info(f"✅ Token blacklisteado")
            except (TokenError, AttributeError) as e:
                logger.warning(f"⚠️ Token blacklist error: {str(e)}")

        # ✅ DESTRUIR SESIÓN DE DJANGO
        request.session.flush()  # Elimina todos los datos de la sesión
        
        # Crear respuesta
        response = success_response(message="Logout exitoso")

        # ✅ ELIMINAR COOKIES JWT
        response.delete_cookie('access_token', path='/', samesite='Lax')
        response.delete_cookie('refresh_token', path='/', samesite='Lax')
        
        # ✅ ELIMINAR COOKIE DE SESIÓN DJANGO
        response.delete_cookie('sessionid', path='/', samesite='Lax')
        response.delete_cookie('csrftoken', path='/', samesite='Lax')

        logger.info(f"✅ Logout exitoso: {request.user.username}")
        logger.info("🍪 Cookies y sesión eliminadas")
        
        return response

    except Exception as e:
        logger.error(f"❌ Error en logout: {str(e)}", exc_info=True)
        
        # Aunque falle, intentar limpiar sesión
        try:
            request.session.flush()
        except:
            pass
            
        return error_response(
            500,
            "Internal Server Error",
            "Error interno del servidor"
        )
