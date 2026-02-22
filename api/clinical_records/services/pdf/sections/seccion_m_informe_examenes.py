# api/clinical_records/services/pdf/sections/seccion_m_informe_examenes.py
"""
Sección M del Formulario 033: INFORME DE EXÁMENES COMPLEMENTARIOS

Muestra los resultados/informes de exámenes complementarios completados,
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

# Colores para resultados
VERDE_NORMAL = colors.HexColor('#D5F5E3')
AZUL_INFORMADO = colors.HexColor('#D4E6F1')
AMARILLO_PENDIENTE = colors.HexColor('#FCF3CF')
GRIS_NO_REALIZADO = colors.HexColor('#F2F4F4')


# ═══════════════════════════════════════════════════════════════════════════
# ESTILOS
# ═══════════════════════════════════════════════════════════════════════════
def _e_titulo():
    return ParagraphStyle(
        'TituloM',
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=BLANCO,
        alignment=TA_CENTER,
        leading=13,
    )

def _e_subtitulo():
    return ParagraphStyle(
        'SubtituloM',
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=VERDE_OSCURO,
        alignment=TA_LEFT,
        leading=11,
        spaceAfter=4,
    )

def _e_header_tabla():
    return ParagraphStyle(
        'HeaderM',
        fontSize=8,
        fontName='Helvetica-Bold',
        textColor=GRIS_ETIQUETA,
        alignment=TA_CENTER,
        leading=10,
    )

def _e_celda_normal():
    return ParagraphStyle(
        'CeldaM',
        fontSize=9,
        fontName='Helvetica',
        textColor=GRIS_TEXTO,
        alignment=TA_LEFT,
        leading=11,
    )

def _e_celda_centrada():
    return ParagraphStyle(
        'CeldaCentradaM',
        fontSize=9,
        fontName='Helvetica',
        textColor=GRIS_TEXTO,
        alignment=TA_CENTER,
        leading=11,
    )

def _e_resultado_normal():
    return ParagraphStyle(
        'ResultadoNormalM',
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#27AE60'),
        alignment=TA_LEFT,
        leading=11,
    )

def _e_resultado_anormal():
    return ParagraphStyle(
        'ResultadoAnormalM',
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#E74C3C'),
        alignment=TA_LEFT,
        leading=11,
    )

def _e_etiqueta():
    return ParagraphStyle(
        'EtiquetaM',
        fontSize=8,
        fontName='Helvetica-Bold',
        textColor=GRIS_ETIQUETA,
        alignment=TA_LEFT,
        leading=10,
    )

def _e_valor():
    return ParagraphStyle(
        'ValorM',
        fontSize=9,
        fontName='Helvetica',
        textColor=GRIS_TEXTO,
        alignment=TA_LEFT,
        leading=11,
    )

def _e_sin_datos():
    return ParagraphStyle(
        'SinDatosM',
        fontSize=9,
        fontName='Helvetica-Oblique',
        textColor=GRIS_ETIQUETA,
        alignment=TA_CENTER,
        leading=12,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL - SECCIÓN M
# ═══════════════════════════════════════════════════════════════════════════
class SeccionMInformeExamenes(BaseSeccion):
    """
    Sección M del Formulario 033: INFORME DE EXÁMENES COMPLEMENTARIOS
    
    Muestra los resultados/informes de exámenes complementarios completados.
    Lee los datos de historial.examenes_complementarios.
    """

    @property
    def nombre_seccion(self) -> str:
        return 'M. Informe de Exámenes Complementarios'

    @property
    def es_opcional(self) -> bool:
        return True  # Opcional porque puede no haber informes

    def construir(self, historial) -> List[Flowable]:
        elementos = []
        elementos.append(self._encabezado('M. INFORME DE EXÁMENES COMPLEMENTARIOS'))
        elementos.append(Spacer(1, 4))

        examen = getattr(historial, 'examenes_complementarios', None)

        informe = getattr(examen, 'informe_examenes', None) if examen else None
        if not examen or not informe or informe == 'NINGUNO':
            elementos.append(Paragraph("No hay informes de exámenes completados", _e_sin_datos()))
            elementos.append(Spacer(1, 8))
            return elementos

        elementos.append(self._tabla_informes([examen]))
        elementos.append(Spacer(1, 6))
        elementos.append(self._estadisticas_informes([examen]))
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
    
    def _tabla_informes(self, informes) -> Table:
        """
        Tabla con los informes de exámenes completados.
        
        Columnas:
            - Fecha
            - Examen
            - Resultado
            - Observaciones
        """
        # Calcular anchos de columna (4 columnas)
        col_w = ANCHO_PAGINA / 4
        
        # Encabezados
        headers = [
            Paragraph('Fecha', _e_header_tabla()),
            Paragraph('Examen', _e_header_tabla()),
            Paragraph('Resultado', _e_header_tabla()),
            Paragraph('Observaciones', _e_header_tabla()),
        ]
        
        # Filas de datos
        filas = [headers]
        for informe in informes:
            # Formatear fecha
            fecha = getattr(informe, 'fecha_modificacion', None) or getattr(informe, 'fecha_creacion', None)
            fecha_str = fecha.strftime('%d/%m/%Y') if fecha else '—'
            
            # Datos del informe
            examen = getattr(informe, 'pedido_examenes', '—')
            resultado = getattr(informe, 'informe_examenes', '—')
            observaciones = getattr(informe, 'informe_examenes_detalle', '—')
            
            if len(observaciones) > 30:
                observaciones = observaciones[:27] + '...'
            
            # Determinar estilo del resultado
            resultado_lower = str(resultado).lower()
            if 'normal' in resultado_lower or 'negativo' in resultado_lower:
                estilo_resultado = _e_resultado_normal()
            else:
                estilo_resultado = _e_resultado_anormal()
            
            filas.append([
                Paragraph(fecha_str, _e_celda_centrada()),
                Paragraph(examen, _e_celda_normal()),
                Paragraph(resultado, estilo_resultado),
                Paragraph(observaciones, _e_celda_normal()),
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
        ]))
        
        return tabla
    
    def _estadisticas_informes(self, informes) -> Table:
        """
        Estadísticas de los informes de exámenes.
        """
        total_informes = len(informes)
        
        # Clasificar resultados
        normales = 0
        anormales = 0
        pendientes_clasificacion = 0
        
        for inf in informes:
            resultado = str(getattr(inf, 'informe_examenes', '')).lower()
            if 'normal' in resultado or 'negativo' in resultado:
                normales += 1
            elif resultado and resultado != 'ninguno':
                anormales += 1
            else:
                pendientes_clasificacion += 1
        
        # Crear tabla de estadísticas
        datos_estadisticas = [
            ['Total Informes', str(total_informes)],
            ['Resultados Normales', str(normales)],
            ['Resultados Anormales', str(anormales)],
        ]
        
        # Calcular anchos
        ancho_etiqueta = 50 * mm
        ancho_valor = 120 * mm
        
        # Crear tabla principal
        tabla_estadisticas = []
        for etiqueta, valor in datos_estadisticas:
            fila = Table(
                [[Paragraph(etiqueta, _e_etiqueta()), Paragraph(valor, _e_valor())]],
                colWidths=[ancho_etiqueta, ancho_valor],
            )
            fila.setStyle(TableStyle([
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
            tabla_estadisticas.append(fila)
            tabla_estadisticas.append(Spacer(1, 2))
        
        # Agrupar en una tabla contenedora
        contenedor = Table([[t] for t in tabla_estadisticas], colWidths=[ANCHO_PAGINA])
        contenedor.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        return contenedor
    
    def sin_datos(self) -> List[Flowable]:
        """Mensaje cuando no hay datos."""
        return [
            Paragraph(
                "<i>No hay informes de exámenes complementarios registrados</i>",
                ESTILOS["normal"],
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionMInformeExamenes']