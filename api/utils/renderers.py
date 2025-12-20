# api/utils/renderers.py
from rest_framework.renderers import JSONRenderer

class StandardizedJSONRenderer(JSONRenderer):
    """
    Renderer que automáticamente envuelve todas las respuestas en formato estándar.
    Maneja tanto respuestas simples como paginadas.
    """
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None
        
        # Si no hay response context, retornar data tal cual (caso de browsable API)
        if not response:
            return super().render(data, accepted_media_type, renderer_context)
        
        # No modificar respuestas que ya están en formato estándar
        if isinstance(data, dict) and 'success' in data and 'status_code' in data:
            return super().render(data, accepted_media_type, renderer_context)
        
        # Estructura estándar de respuesta
        standardized_response = {
            'success': response.status_code < 400,
            'status_code': response.status_code,
            'message': self._get_message(data, response),
            'data': data if response.status_code < 400 else None,
            'errors': data if response.status_code >= 400 else None
        }
        
        return super().render(standardized_response, accepted_media_type, renderer_context)
    
    def _get_message(self, data, response):
        """Genera mensaje automático basado en el status code"""
        status_messages = {
            200: 'Operación exitosa',
            201: 'Recurso creado exitosamente',
            204: 'Recurso eliminado exitosamente',
            400: 'Error en los datos enviados',
            401: 'No autenticado',
            403: 'No tiene permisos para esta acción',
            404: 'Recurso no encontrado',
            500: 'Error interno del servidor'
        }
        
        # Si hay un mensaje personalizado en los datos, usarlo
        if isinstance(data, dict) and 'message' in data:
            return data.pop('message')
        
        return status_messages.get(response.status_code, 'Operación completada')
