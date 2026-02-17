# api/clinical_records/services/pdf/sections/seccion_g_examen_estomatognatico.py
"""
Sección G del Formulario 033: EXAMEN DEL SISTEMA ESTOMATOGNÁTICO

Estructura:
  - Examen extraoral (cabeza, cara, cuello, etc.)
  - Examen intraoral (labios, lengua, paladar, encías, etc.)
  - Oclusión
  - Observaciones

Diseño: Tabla estructurada con subsecciones
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
        'TituloSeccionG',
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=BLANCO,
        alignment=TA_CENTER,
        leading=13,
    )



# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL - SECCIÓN G
# ═══════════════════════════════════════════════════════════════════════════
class SeccionGExamenEstomatognatico(BaseSeccion):
    """
    Sección G del Formulario 033: EXAMEN DEL SISTEMA ESTOMATOGNÁTICO
    
    Muestra el examen completo del sistema estomatognático incluyendo
    examen extraoral, intraoral, oclusión y observaciones.
    """
    
    @property
    def nombre_seccion(self) -> str:
        return 'G. Examen del Sistema Estomatognático'
    
    @property
    def es_opcional(self) -> bool:
        return False  # Siempre debe aparecer
    
    def construir(self, historial) -> List[Flowable]:
        elementos = []

        titulo = Table(
            [[Paragraph('G. EXAMEN DEL SISTEMA ESTOMATOGNÁTICO', _estilo_titulo_seccion())]],
            colWidths=[ANCHO_PAGINA],
        )
        titulo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), VERDE_OSCURO),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elementos.append(titulo)
        elementos.append(Spacer(1, 2))

        examen = historial.examen_estomatognatico

        if not examen:
            elementos.extend(self.sin_datos())
        else:
            # Indicador global sin patología
            if getattr(examen, 'examen_sin_patologia', False):
                elementos.append(self._crear_fila_dato('Estado General', 'Sin patología'))
            else:
                elementos.extend(self._construir_tabla_regiones(examen))

        elementos.append(Spacer(1, 8))
        return elementos

    # ──────────────────────────────────────────────────────────────────────
    # TABLA PRINCIPAL: todas las regiones del modelo real
    # ──────────────────────────────────────────────────────────────────────
    def _construir_tabla_regiones(self, examen) -> List[Flowable]:
        """
        Construye la tabla leyendo los campos reales del modelo.
        Cada región tiene: {region}_cp, {region}_sp, patologías booleanas
        y {region}_descripcion.
        Patrón: region → (Etiqueta, campo_base)
        """
        elementos = []

        # (etiqueta visible, prefijo de campo en el modelo)
        regiones = [
            ('ATM',                  'atm',               'atm_observacion'),
            ('Mejillas',             'mejillas',           'mejillas_descripcion'),
            ('Maxilar Inferior',     'maxilar_inferior',   'maxilar_inferior_descripcion'),
            ('Maxilar Superior',     'maxilar_superior',   'maxilar_superior_descripcion'),
            ('Paladar',              'paladar',            'paladar_descripcion'),
            ('Piso de Boca',         'piso_boca',          'piso_boca_descripcion'),
            ('Carrillos',            'carrillos',          'carrillos_descripcion'),
            ('Glándulas Salivales',  'glandulas_salivales','glandulas_salivales_descripcion'),
            ('Ganglios C/C',         'ganglios',           'ganglios_descripcion'),
            ('Lengua',               'lengua',             'lengua_descripcion'),
            ('Labios',               'labios',             'labios_descripcion'),
        ]

        # Patologías específicas disponibles en el modelo
        patologias_campos = ['absceso', 'fibroma', 'herpes', 'ulcera', 'otra_patologia']
        patologias_labels = ['Absceso', 'Fibroma', 'Herpes', 'Úlcera', 'Otra patología']

        for etiqueta, prefijo, campo_desc in regiones:
            cp = getattr(examen, f'{prefijo}_cp', False)
            sp = getattr(examen, f'{prefijo}_sp', False)
            descripcion = getattr(examen, campo_desc, '') or ''

            # Estado principal
            if cp:
                estado = 'Con Patología'
            elif sp:
                estado = 'Sin Patología'
            else:
                estado = '—'

            # Patologías específicas marcadas
            pats = []
            for pat_campo, pat_label in zip(patologias_campos, patologias_labels):
                if getattr(examen, f'{prefijo}_{pat_campo}', False):
                    pats.append(pat_label)

            # Construir texto de valor
            partes = [estado]
            if pats:
                partes.append('Patologías: ' + ', '.join(pats))
            if descripcion:
                partes.append(descripcion)

            valor = ' | '.join(p for p in partes if p and p != '—') or '—'
            elementos.append(self._crear_fila_dato(etiqueta, valor))

        return elementos
    
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
            colWidths=[50 * mm, 120 * mm],
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
__all__ = ['SeccionGExamenEstomatognatico']