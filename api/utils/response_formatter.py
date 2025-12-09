from rest_framework.response import Response
from rest_framework import status

def format_response(status_code, message=None, data=None, error=None):
    """
    Formato estándar para todas las respuestas
    """
    response_data = {
        "status": status_code,
    }
    
    if message:
        response_data["message"] = message
    
    if data is not None:
        response_data["data"] = data
    
    if error:
        response_data["error"] = error
    
    return Response(response_data, status=status_code)


def success_response(message, data=None, status_code=status.HTTP_200_OK):
    """
    Para respuestas exitosas
    """
    return format_response(
        status_code=status_code,
        message=message,
        data=data
    )


def error_response(status_code, error_type, message):
    """
    Para respuestas de error
    """
    return format_response(
        status_code=status_code,
        error=error_type,
        message=message
    )


def validation_error_response(serializer_errors, message="Error de validación"):
    """
    Para errores de validación
    """
    return Response({
        "status": status.HTTP_400_BAD_REQUEST,
        "error": "Validation Error",
        "message": message,
        "errors": serializer_errors
    }, status=status.HTTP_400_BAD_REQUEST)