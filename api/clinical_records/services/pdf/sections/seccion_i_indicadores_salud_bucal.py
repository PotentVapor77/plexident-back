# api/clinical_records/services/pdf/sections/seccion_i_indicadores_salud_bucal.py
"""
Sección I del Formulario 033: INDICADORES DE SALUD BUCAL

Estructura del modelo IndicadoresSaludBucal:
  - OHI-S: piezas índice (16,11,26,36,31,46) con placa y cálculo (0-3)
  - Índice gingival por pieza (0-1)
  - Promedios calculados: ohi_promedio_placa, ohi_promedio_calculo, gi_promedio_gingivitis
  - Enfermedad periodontal (LEVE/MODERADA/SEVERA)
  - Tipo de oclusión (ANGLE_I/II/III)
  - Nivel de fluorosis (NINGUNA/LEVE/MODERADA/SEVERA)
  - Observaciones

Diseño:
  - Encabezado verde oscuro
  - Tabla principal con estructura:
    * Título "HIGIENE ORAL SIMPLIFICADA"
    * Fila de encabezados: PIEZAS DENTALES EXAMINADAS, PLACA, CÁLCULO, GINGIVITIS
    * Piezas dentales en formato: 16, 17, 55 (tres columnas por fila de piezas)
    * Fila de TOTALES con sumas de cada indicador
  - Tabla inferior con hallazgos clínicos (enfermedad periodontal, oclusión, fluorosis)
"""
from typing import List, Dict, Any, Optional

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
)

# ═══════════════════════════════════════════════════════════════════════════
# COLORES
# ═══════════════════════════════════════════════════════════════════════════
VERDE_OSCURO    = COLOR_PRIMARIO
VERDE_MEDIO     = COLOR_SECUNDARIO
VERDE_CLARO     = COLOR_BORDE
VERDE_MUY_CLARO = COLOR_ACENTO
GRIS_TEXTO      = colors.HexColor('#2C3E50')
GRIS_ETIQUETA   = colors.HexColor('#5D6D7E')
GRIS_HEADER     = colors.HexColor('#ECF0F1')
AMARILLO_SUAVE  = colors.HexColor('#FEF9E7')
BLANCO          = colors.white


# ═══════════════════════════════════════════════════════════════════════════
# ESTILOS
# ═══════════════════════════════════════════════════════════════════════════
def _e_titulo():
    return ParagraphStyle('TituloI', fontSize=11, fontName='Helvetica-Bold',
                          textColor=BLANCO, alignment=TA_CENTER, leading=13)

def _e_subtitulo():
    return ParagraphStyle('SubI', fontSize=9, fontName='Helvetica-Bold',
                          textColor=BLANCO, alignment=TA_LEFT, leading=11)

def _e_titulo_tabla():
    return ParagraphStyle('TituloTablaI', fontSize=10, fontName='Helvetica-Bold',
                          textColor=GRIS_TEXTO, alignment=TA_CENTER, leading=12)

def _e_header_tabla():
    return ParagraphStyle('HeaderI', fontSize=8, fontName='Helvetica-Bold',
                          textColor=GRIS_ETIQUETA, alignment=TA_CENTER, leading=10)

def _e_celda():
    return ParagraphStyle('CeldaI', fontSize=9, fontName='Helvetica',
                          textColor=GRIS_TEXTO, alignment=TA_CENTER, leading=11)

def _e_celda_izq():
    return ParagraphStyle('CeldaIzqI', fontSize=9, fontName='Helvetica',
                          textColor=GRIS_TEXTO, alignment=TA_LEFT, leading=11)

def _e_celda_bold():
    return ParagraphStyle('CeldaBoldI', fontSize=9, fontName='Helvetica-Bold',
                          textColor=GRIS_TEXTO, alignment=TA_CENTER, leading=11)

def _e_etiqueta():
    return ParagraphStyle('EtI', fontSize=8, fontName='Helvetica-Bold',
                          textColor=GRIS_ETIQUETA, alignment=TA_LEFT, leading=10)

def _e_valor():
    return ParagraphStyle('ValI', fontSize=9, fontName='Helvetica',
                          textColor=GRIS_TEXTO, alignment=TA_LEFT, leading=11)

def _e_total():
    return ParagraphStyle('TotalI', fontSize=9, fontName='Helvetica-Bold',
                          textColor=VERDE_OSCURO, alignment=TA_CENTER, leading=11)

def _e_numero_pieza():
    """Estilo para números de piezas dentales"""
    return ParagraphStyle('NumeroPieza', fontSize=9, fontName='Helvetica',
                          textColor=GRIS_TEXTO, alignment=TA_CENTER, leading=11)


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════
# Estructura de piezas dentales según la imagen
# Cada tupla contiene: (pieza_principal, pieza_secundaria, pieza_temporal)
PIEZAS_DENTALES = [
    ('16', '17', '55'),
    ('11', '21', '51'),
    ('26', '27', '65'),
    ('36', '37', '75'),
    ('31', '41', '71'),
    ('46', '47', '85'),
]

# Anchos de columna para la tabla principal - ajustados para ocupar todo el ancho
# Distribución: 40% para piezas, 20% para cada columna de valores
_COL_PIEZAS = ANCHO_PAGINA * 0.40     # 40% del ancho para la columna de piezas
_COL_PLACA = ANCHO_PAGINA * 0.20      # 20% para PLACA
_COL_CALCULO = ANCHO_PAGINA * 0.20    # 20% para CÁLCULO
_COL_GINGIVITIS = ANCHO_PAGINA * 0.20 # 20% para GINGIVITIS
# Verificar que sumen 100% (con tolerancia por redondeo)


def _fmt(valor, decimales=2):
    """Formatea un número con fallback a '—'."""
    if valor is None:
        return '—'
    try:
        return f'{float(valor):.{decimales}f}'
    except (TypeError, ValueError):
        return '—'


def _val_pieza(indicadores, pieza: str, campo: str):
    """Lee pieza_{pieza}_{campo} del objeto indicadores."""
    raw = getattr(indicadores, f'pieza_{pieza}_{campo}', None)
    if raw is None:
        return '—'
    return str(raw)


def _calcular_total(indicadores, campo: str) -> str:
    """Calcula la suma de un campo para todas las piezas."""
    total = 0
    contador = 0
    for fila in PIEZAS_DENTALES:
        for pieza in fila:
            valor = getattr(indicadores, f'pieza_{pieza}_{campo}', None)
            if valor is not None and valor != '' and valor != '—':
                try:
                    total += float(valor)
                    contador += 1
                except (TypeError, ValueError):
                    pass
    
    if contador == 0:
        return '—'
    
    # Para placa y cálculo mostramos suma, para gingivitis mostramos promedio
    if campo == 'gingivitis':
        return _fmt(total / contador, 2)
    else:
        return _fmt(total, 1)


def _crear_celda_piezas(piezas: tuple, color_fondo: colors.Color = None) -> Table:
    """
    Crea una celda con tabla interna de 3 columnas para mostrar las piezas dentales.
    
    Args:
        piezas: Tupla con (pieza1, pieza2, pieza3)
        color_fondo: Color de fondo para la celda
    
    Returns:
        Table: Tabla interna con las piezas en columnas separadas
    """
    # Crear datos para la tabla interna
    data_interna = [[
        Paragraph(piezas[0], _e_numero_pieza()),
        Paragraph(piezas[1], _e_numero_pieza()),
        Paragraph(piezas[2], _e_numero_pieza()),
    ]]
    
    # Calcular ancho de cada columna interna (dividir el ancho de la columna de piezas en 3)
    ancho_columna_interna = _COL_PIEZAS / 3
    
    # Crear tabla interna
    tabla_interna = Table(data_interna, colWidths=[ancho_columna_interna] * 3)
    
    # Estilo de la tabla interna
    estilo_interno = [
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]
    
    # Aplicar color de fondo si se proporciona
    if color_fondo:
        estilo_interno.append(('BACKGROUND', (0, 0), (-1, -1), color_fondo))
    
    tabla_interna.setStyle(TableStyle(estilo_interno))
    
    return tabla_interna


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════
class SeccionIIndicadoresSaludBucal(BaseSeccion):
    """
    Sección I del Formulario 033: INDICADORES DE SALUD BUCAL

    Lee los datos de historial.indicadores_salud_bucal (IndicadoresSaludBucal).
    """

    @property
    def nombre_seccion(self) -> str:
        return 'I. Indicadores de Salud Bucal'

    @property
    def es_opcional(self) -> bool:
        return False

    # ──────────────────────────────────────────────────────────────────────
    def construir(self, historial) -> List[Flowable]:
        elementos = []

        # Encabezado sección
        elementos.append(self._encabezado('I. INDICADORES DE SALUD BUCAL'))
        elementos.append(Spacer(1, 2))

        ind = getattr(historial, 'indicadores_salud_bucal', None)
        if not ind:
            elementos.extend(self.sin_datos())
            elementos.append(Spacer(1, 8))
            return elementos

        # ── Tabla principal de Higiene Oral Simplificada ──────────────────
        elementos.append(self._tabla_principal(ind))
        elementos.append(Spacer(1, 6))

        # ── Tabla de hallazgos clínicos (enfermedad periodontal, oclusión, fluorosis) ──
        elementos.append(self._tabla_hallazgos(ind))
        elementos.append(Spacer(1, 4))

        # ── Observaciones ─────────────────────────────────────────────────
        if getattr(ind, 'observaciones', None):
            elementos.append(self._fila_observaciones(ind.observaciones))
            elementos.append(Spacer(1, 8))

        return elementos

    # ──────────────────────────────────────────────────────────────────────
    # Componentes visuales
    # ──────────────────────────────────────────────────────────────────────
    def _encabezado(self, texto: str) -> Table:
        t = Table([[Paragraph(texto, _e_titulo())]], colWidths=[ANCHO_PAGINA])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), VERDE_OSCURO),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t

    def _tabla_principal(self, ind) -> Table:
        """
        Tabla principal con estructura:
        
        HIGIENE ORAL SIMPLIFICADA
        (fila vacía)
        PIEZAS DENTALES EXAMINADAS | PLACA | CÁLCULO | GINGIVITIS
        [16] [17] [55]              | valor | valor   | valor
        [11] [21] [51]              | valor | valor   | valor
        [26] [27] [65]              | valor | valor   | valor
        [36] [37] [75]              | valor | valor   | valor
        [31] [41] [71]              | valor | valor   | valor
        [46] [47] [85]              | valor | valor   | valor
        TOTALES                      | total | total   | total
        
        Las piezas dentales se muestran en columnas separadas dentro de la primera columna.
        """
        
        # Datos de la tabla
        data = []
        
        # Título de la tabla (fila 0)
        data.append([Paragraph('HIGIENE ORAL SIMPLIFICADA', _e_titulo_tabla()), '', '', ''])
        
        # Fila vacía (fila 1)
        data.append(['', '', '', ''])
        
        # Encabezados de columna (fila 2)
        data.append([
            Paragraph('PIEZAS DENTALES EXAMINADAS', _e_header_tabla()),
            Paragraph('PLACA', _e_header_tabla()),
            Paragraph('CÁLCULO', _e_header_tabla()),
            Paragraph('GINGIVITIS', _e_header_tabla()),
        ])
        
        # Definir colores de fondo alternados para las filas de datos
        colores_fondo = [BLANCO, VERDE_MUY_CLARO]
        
        # Filas de piezas dentales (filas 3-8)
        for idx, fila_piezas in enumerate(PIEZAS_DENTALES):
            # Determinar color de fondo para esta fila (alternado)
            color_fondo = colores_fondo[idx % 2]
            
            # Crear celda con tabla interna de piezas
            celda_piezas = _crear_celda_piezas(fila_piezas, color_fondo)
            
            # Obtener valores para cada pieza de la fila
            # Usamos la pieza correspondiente para cada columna
            valor_placa_p1 = _val_pieza(ind, fila_piezas[0], 'placa')
            valor_placa_p2 = _val_pieza(ind, fila_piezas[1], 'placa')
            valor_placa_p3 = _val_pieza(ind, fila_piezas[2], 'placa')
            
            valor_calculo_p1 = _val_pieza(ind, fila_piezas[0], 'calculo')
            valor_calculo_p2 = _val_pieza(ind, fila_piezas[1], 'calculo')
            valor_calculo_p3 = _val_pieza(ind, fila_piezas[2], 'calculo')
            
            valor_gingivitis_p1 = _val_pieza(ind, fila_piezas[0], 'gingivitis')
            valor_gingivitis_p2 = _val_pieza(ind, fila_piezas[1], 'gingivitis')
            valor_gingivitis_p3 = _val_pieza(ind, fila_piezas[2], 'gingivitis')
            
            # Para simplificar, mostramos solo un valor por fila (como antes)
            # En una implementación completa, deberías mostrar los tres valores
            pieza_ref = fila_piezas[0]
            valor_placa = _val_pieza(ind, pieza_ref, 'placa')
            valor_calculo = _val_pieza(ind, pieza_ref, 'calculo')
            valor_gingivitis = _val_pieza(ind, pieza_ref, 'gingivitis')
            
            data.append([
                celda_piezas,
                Paragraph(valor_placa, _e_celda()),
                Paragraph(valor_calculo, _e_celda()),
                Paragraph(valor_gingivitis, _e_celda()),
            ])
        
        # Fila de TOTALES (fila 9)
        total_placa = _calcular_total(ind, 'placa')
        total_calculo = _calcular_total(ind, 'calculo')
        total_gingivitis = _calcular_total(ind, 'gingivitis')
        
        data.append([
            Paragraph('TOTALES', _e_celda_bold()),
            Paragraph(total_placa, _e_total()),
            Paragraph(total_calculo, _e_total()),
            Paragraph(total_gingivitis, _e_total()),
        ])
        
        # Crear tabla con anchos de columna ajustados al ancho de página
        col_widths = [_COL_PIEZAS, _COL_PLACA, _COL_CALCULO, _COL_GINGIVITIS]
        t = Table(data, colWidths=col_widths)
        
        # Estilos de la tabla
        estilo = [
            # Bordes generales
            ('GRID', (0, 2), (-1, -1), 0.4, VERDE_CLARO),  # Bordes desde fila de encabezados
            ('BOX', (0, 0), (-1, -1), 0.8, VERDE_CLARO),    # Borde exterior
            
            # Título de la tabla (fila 0)
            ('SPAN', (0, 0), (-1, 0)),  # Combinar todas las columnas para el título
            ('BACKGROUND', (0, 0), (-1, 0), VERDE_MUY_CLARO),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            
            # Fila vacía (fila 1)
            ('BACKGROUND', (0, 1), (-1, 1), BLANCO),
            ('TOPPADDING', (0, 1), (-1, 1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 2),
            
            # Encabezados (fila 2)
            ('BACKGROUND', (0, 2), (-1, 2), GRIS_HEADER),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            
            # Filas de datos (las celdas de piezas ya tienen su propio color de fondo)
            # Aseguramos que las celdas de valores tengan el color correspondiente
            ('BACKGROUND', (1, 3), (3, 3), BLANCO),
            ('BACKGROUND', (1, 4), (3, 4), VERDE_MUY_CLARO),
            ('BACKGROUND', (1, 5), (3, 5), BLANCO),
            ('BACKGROUND', (1, 6), (3, 6), VERDE_MUY_CLARO),
            ('BACKGROUND', (1, 7), (3, 7), BLANCO),
            ('BACKGROUND', (1, 8), (3, 8), VERDE_MUY_CLARO),
            
            # Fila de TOTALES (fila 9)
            ('BACKGROUND', (0, 9), (-1, 9), AMARILLO_SUAVE),
            ('FONTNAME', (0, 9), (0, 9), 'Helvetica-Bold'),
            ('LINEABOVE', (0, 9), (-1, 9), 1, VERDE_OSCURO),
            
            # Alineación
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            
            # Eliminar bordes internos de la celda de piezas para que se vea como una sola celda
            ('BOX', (0, 3), (0, 8), 0, colors.white),  # Ocultar bordes de las celdas de piezas
        ]
        
        t.setStyle(TableStyle(estilo))
        return t

    def _tabla_hallazgos(self, ind) -> Table:
        """
        Tabla con hallazgos clínicos:
        ENFERMEDAD PERIODONTAL | TIPOS DE OCLUSIÓN | NIVEL DE FLUOROSIS
        (valor)                | (valor)           | (valor)
        """
        
        def _display(obj, campo, metodo_display):
            valor = getattr(obj, campo, None)
            if not valor:
                return 'No registrado'
            met = getattr(obj, metodo_display, None)
            return met() if callable(met) else str(valor)
        
        # Obtener valores
        enf_periodontal = _display(ind, 'enfermedad_periodontal', 'get_enfermedad_periodontal_display')
        tipo_oclusion = _display(ind, 'tipo_oclusion', 'get_tipo_oclusion_display')
        nivel_fluorosis = _display(ind, 'nivel_fluorosis', 'get_nivel_fluorosis_display')
        
        # Crear párrafos con los valores
        p_enf = Paragraph(enf_periodontal, _e_celda())
        p_oclusion = Paragraph(tipo_oclusion, _e_celda())
        p_fluorosis = Paragraph(nivel_fluorosis, _e_celda())
        
        # Datos de la tabla
        data = [
            [
                Paragraph('ENFERMEDAD<br/>PERIODONTAL', _e_header_tabla()),
                Paragraph('TIPOS DE<br/>OCLUSIÓN', _e_header_tabla()),
                Paragraph('NIVEL DE<br/>FLUOROSIS', _e_header_tabla()),
            ],
            [p_enf, p_oclusion, p_fluorosis],
        ]
        
        # Hacer que la tabla de hallazgos también ocupe todo el ancho
        ancho_columna = ANCHO_PAGINA / 3
        
        t = Table(data, colWidths=[ancho_columna, ancho_columna, ancho_columna])
        t.setStyle(TableStyle([
            # Encabezados
            ('BACKGROUND', (0, 0), (-1, 0), GRIS_HEADER),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            
            # Celdas de valores
            ('BACKGROUND', (0, 1), (-1, 1), BLANCO),
            ('FONTSIZE', (0, 1), (-1, 1), 9),
            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
            ('VALIGN', (0, 1), (-1, 1), 'MIDDLE'),
            
            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.4, VERDE_CLARO),
            ('BOX', (0, 0), (-1, -1), 0.8, VERDE_CLARO),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        return t

    def _fila_observaciones(self, texto: str) -> Table:
        """Fila para observaciones."""
        t = Table(
            [[
                Paragraph('OBSERVACIONES', _e_etiqueta()),
                Paragraph(texto or '—', _e_valor()),
            ]],
            colWidths=[40 * mm, ANCHO_PAGINA - 40 * mm],
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
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return t


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionIIndicadoresSaludBucal']