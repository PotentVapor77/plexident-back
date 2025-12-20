# api/utils/exception_handlers.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Maneja automáticamente todas las excepciones y devuelve formato estándar.
    
    Args:
        exc: Excepción levantada
        context: Contexto de la vista
        
    Returns:
        Response: Respuesta formateada
    """
    # Llamar al handler por defecto de DRF
    response = exception_handler(exc, context)
    
    if response is not None:
        # Log del error para debugging
        logger.error(
            f"API Error: {exc.__class__.__name__} - {str(exc)}",
            extra={'context': context, 'status_code': response.status_code}
        )
        
        # Personalizar formato de error
        custom_response = {
            'success': False,
            'status_code': response.status_code,
            'message': _get_error_message(exc, response),
            'data': None,
            'errors': _format_errors(response.data)
        }
        
        response.data = custom_response
    else:
        # Excepción no manejada por DRF (500 Internal Server Error)
        logger.critical(
            f"Unhandled Exception: {exc.__class__.__name__} - {str(exc)}",
            exc_info=True,
            extra={'context': context}
        )
        
        response = Response(
            {
                'success': False,
                'status_code': 500,
                'message': 'Error interno del servidor',
                'data': None,
                'errors': {'detail': ['Ha ocurrido un error inesperado']}
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return response


def _get_error_message(exc, response):
    """
    Extrae mensaje de error principal.
    
    Args:
        exc: Excepción
        response: Response de DRF
        
    Returns:
        str: Mensaje de error
    """
    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, dict):
            # Tomar el primer mensaje de error
            first_key = list(exc.detail.keys())[0]
            first_error = exc.detail[first_key]
            return str(first_error[0]) if isinstance(first_error, list) else str(first_error)
        return str(exc.detail)
    
    status_messages = {
        400: 'Error en los datos enviados',
        401: 'Credenciales no válidas',
        403: 'No tiene permisos para esta acción',
        404: 'Recurso no encontrado',
        405: 'Método no permitido',
        500: 'Error interno del servidor'
    }
    
    return status_messages.get(response.status_code, 'Error en la solicitud')


def _format_errors(data):
    """
    Formatea errores de validación.
    
    Args:
        data: Datos de error de DRF
        
    Returns:
        dict: Errores formateados
    """
    if isinstance(data, dict):
        errors = {}
        for field, messages in data.items():
            if isinstance(messages, list):
                errors[field] = messages
            elif isinstance(messages, dict):
                # Errores anidados (ej: serializers anidados)
                errors[field] = _format_errors(messages)
            else:
                errors[field] = [str(messages)]
        return errors
    elif isinstance(data, list):
        return {'non_field_errors': data}
    else:
        return {'detail': [str(data)]}
