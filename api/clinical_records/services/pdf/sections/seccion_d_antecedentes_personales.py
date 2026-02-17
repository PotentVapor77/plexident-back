# api/clinical_records/services/pdf/sections/seccion_d_antecedentes_personales.py
"""
Sección D del Formulario 033: ANTECEDENTES PATOLÓGICOS PERSONALES

Estructura:
  - Lista de antecedentes personales del paciente
  - Medicamentos que toma actualmente
  - Alergias
  - Cirugías previas
  - Hábitos

Diseño: Tabla con datos estructurados
"""
from typing import List

from reportlab.platypus import Flowable, Table, TableStyle, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from .base_section import (
    BaseSeccion, 
    ANCHO_PAGINA, 
    ESTILOS,
    COLOR_PRIMARIO, 
    COLOR_SECUNDARIO,
    COLOR_BORDE,
    COLOR_ACENTO,
)


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════
VERDE_OSCURO = COLOR_PRIMARIO
VERDE_MEDIO = COLOR_SECUNDARIO
VERDE_CLARO = COLOR_BORDE
VERDE_MUY_CLARO = COLOR_ACENTO
GRIS_TEXTO = colors.HexColor('#2C3E50')
GRIS_ETIQUETA = colors.HexColor('#5D6D7E')
BLANCO = colors.white


# ═══════════════════════════════════════════════════════════════════════════
# ESTILOS DE TEXTO
# ═══════════════════════════════════════════════════════════════════════════
def _estilo_etiqueta():
    """Etiqueta de campo."""
    return ParagraphStyle(
        'EtiquetaCampo',
        fontSize=8,
        fontName='Helvetica-Bold',
        textColor=GRIS_ETIQUETA,
        leading=10,
        alignment=TA_LEFT,
    )

def _estilo_valor():
    """Valor del campo."""
    return ParagraphStyle(
        'ValorCampo',
        fontSize=9,
        fontName='Helvetica',
        textColor=GRIS_TEXTO,
        leading=11,
        alignment=TA_LEFT,
    )

def _estilo_titulo_seccion():
    """Título de la sección."""
    return ParagraphStyle(
        'TituloSeccionD',
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=BLANCO,
        alignment=TA_CENTER,
        leading=13,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL - SECCIÓN D
# ═══════════════════════════════════════════════════════════════════════════
class SeccionDAntecedentesPersonales(BaseSeccion):
    """
    Sección D del Formulario 033: ANTECEDENTES PATOLÓGICOS PERSONALES
    
    Muestra los antecedentes médicos personales del paciente incluyendo
    enfermedades, medicamentos, alergias, cirugías y hábitos.
    """
    
    @property
    def nombre_seccion(self) -> str:
        return 'D. Antecedentes Patológicos Personales'
    
    @property
    def es_opcional(self) -> bool:
        return False  # Siempre debe aparecer
    
    def construir(self, historial) -> List[Flowable]:
        """
        Construye la sección D.
        
        Args:
            historial: Instancia de ClinicalRecord
            
        Returns:
            Lista de elementos Flowable
        """
        elementos = []
        
        # ═══════════════════════════════════════════════════════════════════
        # ENCABEZADO
        # ═══════════════════════════════════════════════════════════════════
        titulo = Table(
            [[Paragraph(
                'D. ANTECEDENTES PATOLÓGICOS PERSONALES',
                _estilo_titulo_seccion()
            )]],
            colWidths=[ANCHO_PAGINA],
        )
        titulo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), VERDE_OSCURO),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elementos.append(titulo)
        elementos.append(Spacer(1, 2))
        
        # ═══════════════════════════════════════════════════════════════════
        # CONTENIDO
        # ═══════════════════════════════════════════════════════════════════
        
        # Obtener antecedentes
        antecedentes = historial.antecedentes_personales
        
        if not antecedentes:
            # Sin datos
            elementos.extend(self.sin_datos())
        else:
            # Construir tabla con datos
            elementos.extend(self._construir_tabla_antecedentes(antecedentes))
        
        elementos.append(Spacer(1, 8))
        
        return elementos
    
    def _construir_tabla_antecedentes(self, antecedentes) -> List[Flowable]:
        """
        Construye la tabla con los antecedentes personales.
        Usa los campos reales del modelo AntecedentesPersonales.
        """
        elementos = []

        # ── Alergias ──────────────────────────────────────────────────────
        alergia_ab = self._display_con_detalle(
            antecedentes, 'alergia_antibiotico', 'alergia_antibiotico_otro',
            'get_alergia_antibiotico_display', 'NO',
        )
        alergia_an = self._display_con_detalle(
            antecedentes, 'alergia_anestesia', 'alergia_anestesia_otro',
            'get_alergia_anestesia_display', 'NO',
        )

        # ── Hemorragias ───────────────────────────────────────────────────
        hemorragias_val = getattr(antecedentes, 'hemorragias', 'NO')
        hemorragias_det = getattr(antecedentes, 'hemorragias_detalle', '') or ''
        if hemorragias_val == 'SI':
            hemorragias_txt = f"Sí — {hemorragias_det}" if hemorragias_det else 'Sí'
        else:
            hemorragias_txt = 'No'

        # ── Condiciones sistémicas ────────────────────────────────────────
        vih = self._display_con_detalle(
            antecedentes, 'vih_sida', 'vih_sida_otro',
            'get_vih_sida_display', 'NEGATIVO',
        )
        tuberculosis = self._display_con_detalle(
            antecedentes, 'tuberculosis', 'tuberculosis_otro',
            'get_tuberculosis_display', 'NUNCA',
        )
        asma = self._display_con_detalle(
            antecedentes, 'asma', 'asma_otro',
            'get_asma_display', 'NO',
        )
        diabetes = self._display_con_detalle(
            antecedentes, 'diabetes', 'diabetes_otro',
            'get_diabetes_display', 'NO',
        )
        hipertension = self._display_con_detalle(
            antecedentes, 'hipertension_arterial', 'hipertension_arterial_otro',
            'get_hipertension_arterial_display', 'NO',
        )
        cardiaca = self._display_con_detalle(
            antecedentes, 'enfermedad_cardiaca', 'enfermedad_cardiaca_otro',
            'get_enfermedad_cardiaca_display', 'NO',
        )

        # ── Texto libre ───────────────────────────────────────────────────
        otros  = getattr(antecedentes, 'otros_antecedentes_personales', '') or '—'
        habitos = getattr(antecedentes, 'habitos', '') or '—'
        observaciones = getattr(antecedentes, 'observaciones', '') or '—'

        datos = [
            ('Alergia a Antibiótico',   alergia_ab),
            ('Alergia a Anestesia',     alergia_an),
            ('Hemorragias',             hemorragias_txt),
            ('VIH / SIDA',              vih),
            ('Tuberculosis',            tuberculosis),
            ('Asma',                    asma),
            ('Diabetes',                diabetes),
            ('Hipertensión Arterial',   hipertension),
            ('Enfermedad Cardíaca',     cardiaca),
            ('Otros Antecedentes',      otros),
            ('Hábitos',                 habitos),
            ('Observaciones',           observaciones),
        ]

        for etiqueta, valor in datos:
            elementos.append(self._crear_fila_dato(etiqueta, valor))

        return elementos

    def _display_con_detalle(self, obj, campo, campo_otro, metodo_display, valor_negativo) -> str:
        """
        Devuelve el display legible de un campo choice + su detalle '_otro'.
        Si el valor es igual a valor_negativo retorna 'No'.
        """
        valor = getattr(obj, campo, valor_negativo)
        if valor == valor_negativo:
            return 'No'
        # Intentar obtener el display legible via método get_X_display
        metodo = getattr(obj, metodo_display, None)
        texto = metodo() if callable(metodo) else str(valor)
        # Agregar detalle si existe
        detalle = getattr(obj, campo_otro, '') or ''
        if detalle:
            texto += f' — {detalle}'
        return texto
    
    def _crear_fila_dato(self, etiqueta: str, valor: str) -> Table:
        """
        Crea una fila con etiqueta y valor.
        
        Args:
            etiqueta: Etiqueta del campo
            valor: Valor del campo
            
        Returns:
            Tabla con la fila formateada
        """
        etiqueta_para = Paragraph(etiqueta.upper(), _estilo_etiqueta())
        valor_para = Paragraph(valor, _estilo_valor())
        
        tabla = Table(
            [[etiqueta_para, valor_para]],
            colWidths=[60 * mm, 110 * mm],
        )
        
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), VERDE_MUY_CLARO),
            ('BACKGROUND', (1, 0), (1, 0), BLANCO),
            ('BOX', (0, 0), (-1, -1), 0.5, VERDE_CLARO),
            ('LINEAFTER', (0, 0), (0, 0), 0.5, VERDE_CLARO),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        return tabla
    



# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionDAntecedentesPersonales']