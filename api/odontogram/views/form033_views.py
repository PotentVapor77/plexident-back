# api/odontogram/views/form033_views.py

"""
Views para exportación del Formulario 033 Ecuatoriano

Endpoints REST:
- GET /api/odontogram/export/form033/{paciente_id}/json/
- GET /api/odontogram/export/form033/{paciente_id}/html/
- GET /api/odontogram/export/form033/{paciente_id}/pdf/
- POST /api/odontogram/export/form033/{paciente_
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse, HttpResponse
from django.core.files.base import ContentFile
import os
import json
from datetime import datetime

from api.odontogram.services.form033_service import Form033Service


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_form033_json(request, paciente_id):
    """
    Obtiene datos Form 033 en formato JSON
    
    GET /api/odontogram/export/form033/{paciente_id}/json/
    
    Response:
    {
        "seccion_i_paciente": {...},
        "seccion_ii_odontograma": {...},
        "estadisticas": {...}
    }
    """
    try:
        service = Form033Service()
        datos = service.generar_datos_form033(paciente_id)
        
        return Response({
            'estado': 'éxito',
            'datos': datos,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except ValueError as e:
        return Response({
            'estado': 'error',
            'mensaje': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'estado': 'error',
            'mensaje': f'Error interno: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_form033_html(request, paciente_id):
    """
    Obtiene HTML del Formulario 033 para visualizar en navegador
    
    GET /api/odontogram/export/form033/{paciente_id}/html/
    
    Response: HTML renderizable en navegador
    """
    try:
        service = Form033Service()
        html = service.generar_html_form033(paciente_id)
        
        return HttpResponse(html, content_type='text/html; charset=utf-8')
    
    except ValueError as e:
        return HttpResponse(f"<h1>Error: {str(e)}</h1>", status=404)
    
    except Exception as e:
        return HttpResponse(f"<h1>Error interno: {str(e)}</h1>", status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def descargar_form033_pdf(request, paciente_id):
    """
    Genera y descarga PDF del Formulario 033
    
    GET /api/odontogram/export/form033/{paciente_id}/pdf/
    
    Response: Archivo PDF descargable (en memoria, sin guardar en servidor)
    """
    try:
        from weasyprint import HTML, CSS
        from io import BytesIO
        
        service = Form033Service()
        html_content = service.generar_html_form033(paciente_id)
        
        # Generar PDF desde HTML
        html_obj = HTML(string=html_content)
        pdf_bytes = html_obj.write_pdf()
        
        # Crear respuesta descargable
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Form033_{paciente_id}.pdf"'
        
        return response
    
    except ImportError:
        return Response({
            'estado': 'error',
            'mensaje': 'WeasyPrint no está instalado. Ejecuta: pip install weasyprint'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    except ValueError as e:
        return Response({
            'estado': 'error',
            'mensaje': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'estado': 'error',
            'mensaje': f'Error generando PDF: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def guardar_form033_pdf(request, paciente_id):
    """
    Genera y GUARDA PDF en servidor (para auditoría)
    
    POST /api/odontogram/export/form033/{paciente_id}/guardar-pdf/
    
    Guarda en: media/form033_exports/
    
    Response:
    {
        "estado": "éxito",
        "archivo": "Form033_1234567890_20251126_143022.pdf",
        "ruta": "/media/form033_exports/...",
        "timestamp": "2025-11-26T14:30:22.123456"
    }
    """
    try:
        from weasyprint import HTML
        import os
        from django.conf import settings
        
        service = Form033Service()
        html_content = service.generar_html_form033(paciente_id)
        
        # Generar PDF
        html_obj = HTML(string=html_content)
        pdf_bytes = html_obj.write_pdf()
        
        # Crear directorio si no existe
        export_dir = os.path.join(settings.MEDIA_ROOT, 'form033_exports')
        os.makedirs(export_dir, exist_ok=True)
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f'Form033_{paciente_id}_{timestamp}.pdf'
        ruta_completa = os.path.join(export_dir, nombre_archivo)
        
        # Guardar archivo
        with open(ruta_completa, 'wb') as f:
            f.write(pdf_bytes)
        
        return Response({
            'estado': 'éxito',
            'mensaje': 'PDF guardado en servidor',
            'archivo': nombre_archivo,
            'ruta': f'/media/form033_exports/{nombre_archivo}',
            'tamaño_kb': len(pdf_bytes) / 1024,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_201_CREATED)
    
    except ImportError:
        return Response({
            'estado': 'error',
            'mensaje': 'WeasyPrint no está instalado'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    except ValueError as e:
        return Response({
            'estado': 'error',
            'mensaje': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({
            'estado': 'error',
            'mensaje': f'Error guardando PDF: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_exports_form033(request):
    """
    Lista todos los PDFs Form 033 guardados en servidor
    
    GET /api/odontogram/export/form033/exports/
    
    Response:
    {
        "archivos": [
            {
                "nombre": "Form033_...",
                "tamaño_kb": 125.5,
                "fecha": "2025-11-26T14:30:22",
                "url_descarga": "/api/odontogram/export/form033/descargar/..."
            }
        ]
    }
    """
    try:
        import os
        from django.conf import settings
        
        export_dir = os.path.join(settings.MEDIA_ROOT, 'form033_exports')
        
        if not os.path.exists(export_dir):
            return Response({
                'archivos': [],
                'total': 0
            }, status=status.HTTP_200_OK)
        
        archivos = []
        for archivo in sorted(os.listdir(export_dir), reverse=True):
            ruta = os.path.join(export_dir, archivo)
            if os.path.isfile(ruta):
                tamaño = os.path.getsize(ruta)
                fecha_mod = os.path.getmtime(ruta)
                
                archivos.append({
                    'nombre': archivo,
                    'tamaño_kb': round(tamaño / 1024, 2),
                    'fecha': datetime.fromtimestamp(fecha_mod).isoformat(),
                    'url_descarga': f'/api/odontogram/export/form033/descargar/{archivo}/'
                })
        
        return Response({
            'archivos': archivos,
            'total': len(archivos)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'estado': 'error',
            'mensaje': f'Error listando archivos: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def descargar_pdf_guardado(request, nombre_archivo):
    """
    Descarga un PDF guardado previamente
    
    GET /api/odontogram/export/form033/descargar/{nombre_archivo}/
    
    Response: Archivo PDF descargable
    """
    try:
        import os
        from django.conf import settings
        
        export_dir = os.path.join(settings.MEDIA_ROOT, 'form033_exports')
        ruta_archivo = os.path.join(export_dir, nombre_archivo)
        
        # Prevención de directory traversal
        if not os.path.abspath(ruta_archivo).startswith(os.path.abspath(export_dir)):
            return Response({
                'estado': 'error',
                'mensaje': 'Acceso denegado'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not os.path.exists(ruta_archivo):
            return Response({
                'estado': 'error',
                'mensaje': 'Archivo no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        
        response = FileResponse(open(ruta_archivo, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        
        return response
    
    except Exception as e:
        return Response({
            'estado': 'error',
            'mensaje': f'Error descargando archivo: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)