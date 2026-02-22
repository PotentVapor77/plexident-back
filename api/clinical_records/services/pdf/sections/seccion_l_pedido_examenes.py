# api/clinical_records/services/pdf/sections/seccion_l_pedido_examenes.py
"""
Sección L del Formulario 033: PEDIDO DE EXÁMENES COMPLEMENTARIOS

Muestra los exámenes complementarios solicitados (pedidos pendientes)
siguiendo el diseño consistente con otras secciones del formulario.
"""
from typing import List
from datetime import datetime

from reportlab.platypus import Flowable, Table, TableStyle, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from .base_section import (
    BaseSeccion,
    ANCHO_PAGINA,
    COLOR_PRIMARIO,
    COLOR_SECUNDARIO,
    COLOR_BORDE,
    COLOR_ACENTO,
    ESTILOS,
)


# ═══════════════════════════════════════════════════════════════════════════
# COLORES
# ═══════════════════════════════════════════════════════════════════════════
VERDE_OSCURO = COLOR_PRIMARIO    # #2E7D32
VERDE_MEDIO = COLOR_SECUNDARIO    # #81C784
VERDE_CLARO = COLOR_BORDE         # #A5D6A7
VERDE_MUY_CLARO = COLOR_ACENTO    # #EDF2F7
GRIS_TEXTO = colors.HexColor('#2C3E50')
GRIS_ETIQUETA = colors.HexColor('#5D6D7E')
GRIS_HEADER = colors.HexColor('#ECF0F1')
BLANCO = colors.white

# Colores de estado
AMARILLO_PENDIENTE = colors.HexColor('#FCF3CF')
AZUL_COMPLETADO = colors.HexColor('#D4E6F1')
ROJO_ALERTA = colors.HexColor('#FADBD8')


# ═══════════════════════════════════════════════════════════════════════════
# ESTILOS
# ═══════════════════════════════════════════════════════════════════════════
def _e_titulo():
    return ParagraphStyle(
        'TituloL',
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=BLANCO,
        alignment=TA_CENTER,
        leading=13,
    )

def _e_subtitulo():
    return ParagraphStyle(
        'SubtituloL',
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=VERDE_OSCURO,
        alignment=TA_LEFT,
        leading=11,
        spaceAfter=4,
    )

def _e_header_tabla():
    return ParagraphStyle(
        'HeaderL',
        fontSize=8,
        fontName='Helvetica-Bold',
        textColor=GRIS_ETIQUETA,
        alignment=TA_CENTER,
        leading=10,
    )

def _e_celda_normal():
    return ParagraphStyle(
        'CeldaL',
        fontSize=9,
        fontName='Helvetica',
        textColor=GRIS_TEXTO,
        alignment=TA_LEFT,
        leading=11,
    )

def _e_celda_centrada():
    return ParagraphStyle(
        'CeldaCentradaL',
        fontSize=9,
        fontName='Helvetica',
        textColor=GRIS_TEXTO,
        alignment=TA_CENTER,
        leading=11,
    )

def _e_estado_pendiente():
    return ParagraphStyle(
        'EstadoPendienteL',
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#B7950B'),
        alignment=TA_CENTER,
        leading=11,
    )

def _e_etiqueta():
    return ParagraphStyle(
        'EtiquetaL',
        fontSize=8,
        fontName='Helvetica-Bold',
        textColor=GRIS_ETIQUETA,
        alignment=TA_LEFT,
        leading=10,
    )

def _e_valor():
    return ParagraphStyle(
        'ValorL',
        fontSize=9,
        fontName='Helvetica',
        textColor=GRIS_TEXTO,
        alignment=TA_LEFT,
        leading=11,
    )

def _e_sin_datos():
    return ParagraphStyle(
        'SinDatosL',
        fontSize=9,
        fontName='Helvetica-Oblique',
        textColor=GRIS_ETIQUETA,
        alignment=TA_CENTER,
        leading=12,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL - SECCIÓN L
# ═══════════════════════════════════════════════════════════════════════════
class SeccionLPedidoExamenes(BaseSeccion):
    """
    Sección L del Formulario 033: PEDIDO DE EXÁMENES COMPLEMENTARIOS
    
    Muestra los exámenes complementarios solicitados (pedidos pendientes).
    Lee los datos de historial.examenes_complementarios.
    """

    @property
    def nombre_seccion(self) -> str:
        return 'L. Pedido de Exámenes Complementarios'

    @property
    def es_opcional(self) -> bool:
        return True  # Opcional porque puede no haber pedidos

    def construir(self, historial) -> List[Flowable]:
        """
        Construye la sección L del Formulario 033: PEDIDO DE EXÁMENES COMPLEMENTARIOS
        """
        elementos = []
        elementos.append(self._encabezado('L. PEDIDO DE EXÁMENES COMPLEMENTARIOS'))
        elementos.append(Spacer(1, 4))

        examen = getattr(historial, 'examenes_complementarios', None)
        
        if not examen or getattr(examen, 'pedido_examenes', 'NO') != 'SI':
            elementos.append(Paragraph("No hay pedidos de exámenes pendientes", _e_sin_datos()))
            elementos.append(Spacer(1, 8))
            return elementos
        
        
        elementos.append(self._tabla_pedidos([examen]))
        elementos.append(Spacer(1, 6))
        elementos.append(self._resumen_pedidos([examen]))
        elementos.append(Spacer(1, 8))
        return elementos
        
    # ──────────────────────────────────────────────────────────────────────
    # Componentes visuales
    # ──────────────────────────────────────────────────────────────────────
    
    def _encabezado(self, texto: str) -> Table:
        """Encabezado de sección con color verde oscuro."""
        t = Table(
            [[Paragraph(texto, _e_titulo())]],
            colWidths=[ANCHO_PAGINA],
        )
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), VERDE_OSCURO),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t
    
    def _tabla_pedidos(self, pedidos) -> Table:
        """
        Tabla con los pedidos de exámenes pendientes.
        
        Columnas:
            - Fecha
            - Examen Solicitado
            - Detalle
            - Estado
        """
        # Calcular anchos de columna (4 columnas)
        col_w = ANCHO_PAGINA / 4
        
        # Encabezados
        headers = [
            Paragraph('Fecha', _e_header_tabla()),
            Paragraph('Examen', _e_header_tabla()),
            Paragraph('Detalle', _e_header_tabla()),
            Paragraph('Estado', _e_header_tabla()),
        ]
        
        # Filas de datos
        filas = [headers]
        for pedido in pedidos:
            # Formatear fecha
            fecha = getattr(pedido, 'fecha_creacion', None)
            fecha_str = fecha.strftime('%d/%m/%Y') if fecha else '—'
            
            # Datos del pedido
            examen = getattr(pedido, 'pedido_examenes', '—')
            detalle = getattr(pedido, 'pedido_examenes_detalle', '—')
            if len(detalle) > 40:
                detalle = detalle[:37] + '...'
            
            filas.append([
                Paragraph(fecha_str, _e_celda_centrada()),
                Paragraph(examen, _e_celda_normal()),
                Paragraph(detalle, _e_celda_normal()),
                Paragraph('PENDIENTE', _e_estado_pendiente()),
            ])
        
        # Crear tabla
        tabla = Table(filas, colWidths=[col_w] * 4, repeatRows=1)
        
        # Estilos
        tabla.setStyle(TableStyle([
            # Encabezados
            ('BACKGROUND', (0, 0), (-1, 0), GRIS_HEADER),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, VERDE_CLARO),
            ('BOX', (0, 0), (-1, -1), 1, VERDE_CLARO),
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            # Filas alternadas
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BLANCO, VERDE_MUY_CLARO]),
            # Resaltar estado pendiente
            ('BACKGROUND', (3, 1), (3, -1), AMARILLO_PENDIENTE),
        ]))
        
        return tabla
    
    def _resumen_pedidos(self, pedidos) -> Table:
        """
        Resumen de pedidos con contadores.
        """
        total_pedidos = len(pedidos)
        
        # Calcular pedidos por tipo (simplificado)
        tipos = {}
        for p in pedidos:
            tipo = getattr(p, 'pedido_examenes', 'Otros')
            tipos[tipo] = tipos.get(tipo, 0) + 1
        
        # Crear texto de resumen
        resumen = f"Total de pedidos pendientes: {total_pedidos}"
        if tipos:
            resumen += " | "
            resumen += " | ".join([f"{k}: {v}" for k, v in tipos.items()])
        
        # Tabla de resumen
        t = Table(
            [[
                Paragraph('RESUMEN DE PEDIDOS', _e_etiqueta()),
                Paragraph(resumen, _e_valor()),
            ]],
            colWidths=[50 * mm, 120 * mm],
        )
        
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), VERDE_MUY_CLARO),
            ('BACKGROUND', (1, 0), (1, 0), BLANCO),
            ('BOX', (0, 0), (-1, -1), 0.5, VERDE_CLARO),
            ('LINEAFTER', (0, 0), (0, 0), 0.5, VERDE_CLARO),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        return t
    
    def sin_datos(self) -> List[Flowable]:
        """Mensaje cuando no hay datos."""
        return [
            Paragraph(
                "<i>No hay pedidos de exámenes complementarios registrados</i>",
                ESTILOS["normal"],
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionLPedidoExamenes']