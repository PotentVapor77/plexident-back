# api/clinical_records/services/pdf/sections/base_section.py
"""
Clase base para todas las secciones del PDF del historial clínico.
Cada sección es independiente y produce su propio bloque de elementos ReportLab.
"""
from abc import ABC, abstractmethod
from typing import List

from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ─── Paleta de colores del sistema ─────────────────────────────────────────
COLOR_PRIMARIO    = colors.HexColor('#1B4F72')   # Azul oscuro cabeceras
COLOR_SECUNDARIO  = colors.HexColor('#2E86C1')   # Azul medio subencabezados
COLOR_ACENTO      = colors.HexColor('#D6EAF8')   # Azul muy claro fondo filas
COLOR_BORDE       = colors.HexColor('#AED6F1')   # Borde tablas
COLOR_TEXTO       = colors.HexColor('#1C2833')   # Texto principal
COLOR_SUBTEXTO    = colors.HexColor('#5D6D7E')   # Texto secundario
COLOR_VACIO       = colors.HexColor('#F2F3F4')   # Fondo cuando sin datos
COLOR_EXITO       = colors.HexColor('#1E8449')   # Verde para valores normales
COLOR_ADVERTENCIA = colors.HexColor('#B7950B')   # Amarillo advertencia


def _build_styles() -> dict:
    """Construye el diccionario de estilos reutilizables."""
    base = getSampleStyleSheet()

    def ps(name, **kwargs) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base['Normal'], **kwargs)

    return {
        'titulo_seccion': ps(
            'TituloSeccion',
            fontSize=11, fontName='Helvetica-Bold',
            textColor=colors.white, spaceAfter=2,
            leftIndent=4,
        ),
        'subtitulo': ps(
            'Subtitulo',
            fontSize=9, fontName='Helvetica-Bold',
            textColor=COLOR_PRIMARIO, spaceBefore=4, spaceAfter=2,
        ),
        'etiqueta': ps(
            'Etiqueta',
            fontSize=8, fontName='Helvetica-Bold',
            textColor=COLOR_SUBTEXTO,
        ),
        'valor': ps(
            'Valor',
            fontSize=9, fontName='Helvetica',
            textColor=COLOR_TEXTO,
        ),
        'valor_sin_datos': ps(
            'ValorSinDatos',
            fontSize=8, fontName='Helvetica-Oblique',
            textColor=COLOR_SUBTEXTO,
        ),
        'normal': ps(
            'Normal2',
            fontSize=9, fontName='Helvetica',
            textColor=COLOR_TEXTO, spaceAfter=2,
        ),
        'pie_pagina': ps(
            'PiePagina',
            fontSize=7, fontName='Helvetica',
            textColor=COLOR_SUBTEXTO, alignment=TA_CENTER,
        ),
    }


ESTILOS = _build_styles()
ANCHO_PAGINA = 170 * mm   # Ancho útil A4 con márgenes de 20mm


class BaseSeccion(ABC):
    """
    Clase base abstracta para todas las secciones del PDF.

    Para agregar una nueva sección al PDF basta con:
    1. Crear una clase que herede de BaseSeccion
    2. Implementar `nombre_seccion` y `construir()`
    3. Registrarla en ClinicalRecordPDFBuilder
    """

    @property
    @abstractmethod
    def nombre_seccion(self) -> str:
        """Nombre legible de la sección (se usa en el encabezado)."""

    @property
    def es_opcional(self) -> bool:
        """Si True, la sección se omite cuando no tiene datos."""
        return True

    @abstractmethod
    def construir(self, historial) -> List[Flowable]:
        """
        Construye y retorna la lista de elementos Flowable de esta sección.
        Retorna lista vacía si no hay datos y es_opcional=True.
        """

    # ─── Helpers compartidos ────────────────────────────────────────────────

    def encabezado_seccion(self, titulo: str) -> List[Flowable]:
        """Genera el bloque de encabezado con fondo de color."""
        tabla = Table(
            [[Paragraph(titulo.upper(), ESTILOS['titulo_seccion'])]],
            colWidths=[ANCHO_PAGINA],
        )
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_PRIMARIO),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ]))
        return [tabla, Spacer(1, 3)]

    def fila_dato(self, etiqueta: str, valor, ancho_etiqueta=55*mm) -> Table:
        """Fila de dos columnas: etiqueta → valor."""
        valor_str = str(valor) if valor not in (None, '', []) else '—'
        estilo_valor = ESTILOS['valor'] if valor_str != '—' else ESTILOS['valor_sin_datos']

        t = Table(
            [[
                Paragraph(etiqueta, ESTILOS['etiqueta']),
                Paragraph(valor_str, estilo_valor),
            ]],
            colWidths=[ancho_etiqueta, ANCHO_PAGINA - ancho_etiqueta],
        )
        t.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 0), (-1, -1), 0.3, COLOR_BORDE),
        ]))
        return t

    def tabla_datos(
        self,
        filas: list,
        encabezados: list = None,
        col_widths: list = None,
    ) -> Table:
        """Tabla genérica con estilo consistente."""
        data = []
        if encabezados:
            data.append([Paragraph(str(h), ESTILOS['etiqueta']) for h in encabezados])

        for fila in filas:
            data.append([
                Paragraph(str(celda) if celda not in (None, '') else '—', ESTILOS['valor'])
                for celda in fila
            ])

        if not data:
            return None

        col_widths = col_widths or [ANCHO_PAGINA / len(data[0])] * len(data[0])
        t = Table(data, colWidths=col_widths, repeatRows=1 if encabezados else 0)

        estilo = [
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.3, COLOR_BORDE),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, COLOR_ACENTO]),
        ]
        if encabezados:
            estilo += [
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_SECUNDARIO),
                ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
                ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]
        t.setStyle(TableStyle(estilo))
        return t

    def sin_datos(self) -> List[Flowable]:
        """Bloque estándar cuando la sección no tiene datos."""
        t = Table(
            [[Paragraph('Sin datos registrados', ESTILOS['valor_sin_datos'])]],
            colWidths=[ANCHO_PAGINA],
        )
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_VACIO),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ]))
        return [t, Spacer(1, 6)]