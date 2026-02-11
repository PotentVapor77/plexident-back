# api/odontogram/views/form033_views.py

"""
Views para exportación del Formulario 033 Ecuatoriano

Endpoints REST:
- GET  /api/odontogram/export/form033/{paciente_id}/json/
- GET  /api/odontogram/export/form033/{paciente_id}/html/
- GET  /api/odontogram/export/form033/{paciente_id}/pdf/
- POST /api/odontogram/export/form033/{paciente_id}/guardar-pdf/
- GET  /api/odontogram/export/form033/exports/
- GET  /api/odontogram/export/form033/descargar/{nombre_archivo}/
"""

import os
from datetime import datetime

from django.http import FileResponse, HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.odontogram.services.form033_service import Form033Service


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def obtener_form033_json(request, paciente_id):
    """
    GET /api/odontogram/export/form033/{paciente_id}/json/

    Devuelve la estructura JSON completa para el Form 033:
    {
        "timestamp": "...",
        "form033": { ... }
    }
    """
    service = Form033Service()
    try:
        datos = service.generar_datos_form033(paciente_id)
    except ValueError as e:
        # 404 estándar, lo envuelve custom_exception_handler
        raise NotFound(detail=str(e))

    return Response(
        {
            "timestamp": datetime.now().isoformat(),
            "form033": datos,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def obtener_form033_html(request, paciente_id):
    """
    GET /api/odontogram/export/form033/{paciente_id}/html/

    Devuelve HTML renderizable en el navegador.
    """
    service = Form033Service()
    try:
        html = service.generar_html_form033(paciente_id)
    except ValueError as e:
        # Aquí se responde HTML plano, fuera del renderer JSON
        return HttpResponse(str(e), status=status.HTTP_404_NOT_FOUND)

    return HttpResponse(html, content_type="text/html; charset=utf-8")





@api_view(["GET"])
@permission_classes([IsAuthenticated])
def listar_exports_form033(request):
    """
    Lista todos los PDFs Form 033 guardados en servidor

    GET /api/odontogram/export/form033/exports/

    Respuesta:
    {
        "archivos": [
            {
                "nombre": "Form033_...",
                "tamaño_kb": 125.5,
                "fecha": "2025-11-26T14:30:22",
                "url_descarga": "/api/odontogram/export/form033/descargar/..."
            },
            ...
        ],
        "total": 3
    }
    """
    try:
        from django.conf import settings

        export_dir = os.path.join(settings.MEDIA_ROOT, "form033_exports")

        if not os.path.exists(export_dir):
            return Response(
                {
                    "archivos": [],
                    "total": 0,
                },
                status=status.HTTP_200_OK,
            )

        archivos = []
        for archivo in sorted(os.listdir(export_dir), reverse=True):
            ruta = os.path.join(export_dir, archivo)
            if os.path.isfile(ruta):
                tamaño = os.path.getsize(ruta)
                fecha_mod = os.path.getmtime(ruta)
                archivos.append(
                    {
                        "nombre": archivo,
                        "tamaño_kb": round(tamaño / 1024, 2),
                        "fecha": datetime.fromtimestamp(fecha_mod).isoformat(),
                        "url_descarga": f"/api/odontogram/export/form033/descargar/{archivo}/",
                    }
                )

        return Response(
            {
                "archivos": archivos,
                "total": len(archivos),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {
                "estado": "error",
                "mensaje": f"Error listando archivos: {str(e)}",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def descargar_pdf_guardado(request, nombre_archivo):
    """
    Descarga un PDF guardado previamente

    GET /api/odontogram/export/form033/descargar/{nombre_archivo}/

    Response: Archivo PDF descargable.
    """
    try:
        from django.conf import settings

        export_dir = os.path.join(settings.MEDIA_ROOT, "form033_exports")
        ruta_archivo = os.path.join(export_dir, nombre_archivo)

        # Prevención de directory traversal
        if not os.path.abspath(ruta_archivo).startswith(os.path.abspath(export_dir)):
            return Response(
                {
                    "estado": "error",
                    "mensaje": "Acceso denegado",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not os.path.exists(ruta_archivo):
            return Response(
                {
                    "estado": "error",
                    "mensaje": "Archivo no encontrado",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        response = FileResponse(
            open(ruta_archivo, "rb"),
            content_type="application/pdf",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{nombre_archivo}"'
        )
        return response

    except Exception as e:
        return Response(
            {
                "estado": "error",
                "mensaje": f"Error descargando archivo: {str(e)}",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
