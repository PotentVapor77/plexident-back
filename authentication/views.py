"""
============================================================================
AUTHENTICATION VIEWS
============================================================================
Endpoints de autenticación con JWT en HttpOnly cookies
"""

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from api.users.models import Usuario
from authentication.serializers import (
    AuthUserSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
)

logger = logging.getLogger(__name__)


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
    """
    #  Validar datos de entrada con serializer
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)  #  El exception handler maneja errores
    
    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    
    #  Autenticar usuario
    usuario = authenticate(request, username=username, password=password)
    
    if not usuario:
        raise AuthenticationFailed('Usuario o contraseña incorrectos')
    
    if not usuario.is_active:
        raise PermissionDenied('Cuenta desactivada')
    
    # Generar tokens JWT
    refresh = RefreshToken.for_user(usuario)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)
    
    # Serializar datos del usuario
    user_data = AuthUserSerializer(usuario).data
    
    logger.info(f" Login exitoso: {usuario.username}")
    
    #  Crear respuesta simple - el renderer la formatea
    response = Response({
        'user': user_data,
        'message': 'Login exitoso'
    }, status=status.HTTP_200_OK)
    
    # Guardar tokens en cookies
    set_auth_cookie(response, 'access_token', access_token, 3600)  # 1 hora
    set_auth_cookie(response, 'refresh_token', refresh_token, 604800)  # 7 días
    
    return response


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
    usuario = request.user
    
    if not usuario or not usuario.is_authenticated:
        raise AuthenticationFailed('No autenticado')
    
    user_data = AuthUserSerializer(usuario).data
    
    # Respuesta simple - el renderer la formatea
    return Response({
        'user': user_data,
        'message': 'Usuario obtenido exitosamente'
    })


# ============================================================================
# REFRESH TOKEN
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token_view(request):
    """
    Endpoint para refrescar tokens.
    
    Si ROTATE_REFRESH_TOKENS=True, genera nuevo refresh token.
    """
    # Leer refresh token de cookies
    refresh_token = request.COOKIES.get('refresh_token')
    
    if not refresh_token:
        raise AuthenticationFailed('No hay refresh token disponible')
    
    try:
        # Validar refresh token
        old_refresh = RefreshToken(refresh_token)
        
        # Obtener user_id del token
        user_id = old_refresh.payload.get('user_id')
        if not user_id:
            raise TokenError("Token no contiene user_id")
        
        # Obtener usuario
        usuario = get_object_or_404(Usuario, id=user_id)
        
        # Verificar si rotation está habilitado
        simple_jwt_settings = getattr(settings, 'SIMPLE_JWT', {})
        rotate_refresh = simple_jwt_settings.get('ROTATE_REFRESH_TOKENS', False)
        blacklist_after = simple_jwt_settings.get('BLACKLIST_AFTER_ROTATION', False)
        
        
        #  Crear respuesta simple
        response = Response({
            'refreshed': True,
            'message': 'Token refrescado exitosamente'
        })
        
        if rotate_refresh:
            # Rotación de tokens habilitada
            if blacklist_after:
                try:
                    old_refresh.blacklist()
                    logger.info("Token antiguo blacklisteado")
                except AttributeError:
                    logger.warning("Blacklist no disponible")
                except Exception as e:
                    logger.warning(f"Error al blacklistear: {str(e)}")
            
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
        
        logger.info(f"Token refresh exitoso para: {usuario.username}")
        return response
        
    except TokenError as e:
        logger.warning(f"Token inválido o expirado: {str(e)}")
        raise AuthenticationFailed('Refresh token inválido o expirado')


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
    # Leer refresh token de cookies
    refresh_token = request.COOKIES.get('refresh_token')
    
    if refresh_token:
        try:
            # Blacklist el refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("Token blacklisteado")
        except (TokenError, AttributeError) as e:
            logger.warning(f"⚠️ Token blacklist error: {str(e)}")
    
    # Destruir sesión de Django
    request.session.flush()
    
    #  Crear respuesta simple
    response = Response({'message': 'Logout exitoso'})
    
    # Eliminar cookies JWT
    response.delete_cookie('access_token', path='/', samesite='Lax')
    response.delete_cookie('refresh_token', path='/', samesite='Lax')
    
    # Eliminar cookie de sesión Django
    response.delete_cookie('sessionid', path='/', samesite='Lax')
    response.delete_cookie('csrftoken', path='/', samesite='Lax')
    
    logger.info(f"Logout exitoso: {request.user.username}")
    logger.info(" Cookies y sesión eliminadas")
    
    return response


# ============================================================================
# PASSWORD RESET
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_view(request):
    """Envía email con token de reset"""
    #  Validar con serializer
    serializer = PasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    
    try:
        user = Usuario.objects.get(correo__iexact=email, is_active=True)
        
        # Generar token único
        token = secrets.token_urlsafe(32)
        expiry = timezone.now() + timedelta(hours=1)
        
        user.reset_password_token = token
        user.reset_password_expires = expiry
        user.save()
        
        # URL de reseteo
        reset_url = (
            f"{settings.FRONTEND_URL}/reset-password/"
            f"{urlsafe_base64_encode(force_bytes(user.pk))}/{token}"
        )
        
        subject = "Recuperar contraseña - FamySALUD"
        from_email = settings.DEFAULT_FROM_EMAIL
        to = [email]
        
        # Texto plano (fallback)
        text_content = (
            f"Hola {user.nombres},\n\n"
            f"Haz clic en el siguiente enlace para restablecer tu contraseña:\n"
            f"{reset_url}\n\n"
            "Si no solicitaste este cambio, puedes ignorar este mensaje."
        )
        
        # HTML desde template
        html_content = render_to_string(
            "emails/password_reset.html",
            {
                "user": user,
                "reset_url": reset_url,
                "year": timezone.now().year,
            },
        )
        
        msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        logger.info(f"Email de reset enviado a {email}")
        
    except Usuario.DoesNotExist:
        # No revelar si el email existe o no (seguridad)
        pass
    
    #  Siempre retornar éxito (seguridad)
    return Response({
        'message': 'Si el email existe, recibirás instrucciones para resetear tu contraseña'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm_view(request):
    """Confirma reset con token y nueva contraseña"""
    #  Validar con serializer
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    try:
        uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
        token = serializer.validated_data['token']
        password = serializer.validated_data['new_password']
        
        user = Usuario.objects.get(pk=uid, reset_password_token=token)
        
        # Validar expiración
        if user.reset_password_expires < timezone.now():
            raise ValidationError({'detail': 'El enlace ha expirado'})
        
        # Actualizar password
        user.set_password(password)
        user.reset_password_token = None
        user.reset_password_expires = None
        user.save()
        
        logger.info(f"Contraseña reseteada para usuario {user.username}")
        
        #  Respuesta simple
        return Response({
            'message': 'Contraseña actualizada exitosamente'
        })
        
    except (Usuario.DoesNotExist, TypeError, ValueError):
        raise ValidationError({'detail': 'Token inválido o expirado'})
