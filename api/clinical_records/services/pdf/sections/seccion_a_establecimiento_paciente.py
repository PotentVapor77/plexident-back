# api/clinical_records/services/pdf/sections/seccion_a_establecimiento_paciente.py
"""
Sección A del Formulario 033: DATOS DE ESTABLECIMIENTO Y USUARIO / PACIENTE

Estructura oficial:
  Fila A (Establecimiento):
    - INSTITUCIÓN DEL SISTEMA
    - UNICÓDIGO
    - ESTABLECIMIENTO DE SALUD
    - NÚMERO DE ARCHIVO
    - No. HOJA

  Fila B (Paciente):
    - APELLIDO
    - NOMBRE
    - SEXO
    - EDAD
    - CONDICIÓN EDAD (H/D/M/A)

Diseño: UI unificada con color verde médico, sin separación de grid.
"""
from typing import List
from datetime import datetime

from reportlab.platypus import Flowable, Table, TableStyle, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from .base_section import BaseSeccion, ANCHO_PAGINA, COLOR_PRIMARIO, COLOR_SECUNDARIO, COLOR_TERCIARIO


# ═══════════════════════════════════════════════════════════════════════════════
# PALETA DE COLORES - VERDE MÉDICO PROFESIONAL
# ═══════════════════════════════════════════════════════════════════════════════
VERDE_OSCURO = COLOR_PRIMARIO           # '#117A65' - Encabezado principal
VERDE_MEDIO = COLOR_SECUNDARIO          # '#16A085' - Encabezado secundario
VERDE_CLARO = colors.HexColor('#A3E4D7') # Bordes
VERDE_MUY_CLARO = colors.HexColor('#D0ECE7') # Fondo alterno
GRIS_TEXTO = colors.HexColor('#2C3E50')       # Texto principal
GRIS_ETIQUETA = colors.HexColor('#5D6D7E')    # Etiquetas
BLANCO = colors.white


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES DE ALTURA - TODAS LAS CELDAS CON LA MISMA ALTURA
# ═══════════════════════════════════════════════════════════════════════════════
ALTURA_FILA_ETIQUETA = 6 * mm
ALTURA_FILA_VALOR = 8 * mm
ALTURA_TOTAL_CELDA = ALTURA_FILA_ETIQUETA + ALTURA_FILA_VALOR


# ═══════════════════════════════════════════════════════════════════════════════
# ESTILOS DE TEXTO
# ═══════════════════════════════════════════════════════════════════════════════
def _estilo_etiqueta(size=7, alignment=TA_LEFT):
    """Etiqueta de campo en mayúsculas."""
    return ParagraphStyle(
        'EtiquetaCampo',
        fontSize=size,
        fontName='Helvetica-Bold',
        textColor=GRIS_ETIQUETA,
        leading=size + 2,
        alignment=alignment,
    )

def _estilo_valor(size=9, bold=False, alignment=TA_LEFT):
    """Valor del campo."""
    return ParagraphStyle(
        'ValorCampo',
        fontSize=size,
        fontName='Helvetica-Bold' if bold else 'Helvetica',
        textColor=GRIS_TEXTO,
        leading=size + 2,
        alignment=alignment,
    )

def _estilo_titulo_seccion():
    """Título de la sección completa."""
    return ParagraphStyle(
        'TituloSeccionA',
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=BLANCO,
        alignment=TA_CENTER,
        leading=13,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER ÚNICO PARA CREAR CELDAS - TODAS CON LA MISMA ALTURA
# ═══════════════════════════════════════════════════════════════════════════════
def _crear_celda(etiqueta: str, valor, ancho: float, alignment=TA_LEFT) -> Table:
    """
    Crea una celda individual con etiqueta arriba y valor abajo.
    TODAS las celdas tienen la MISMA ALTURA independientemente del tipo.
    
    Args:
        etiqueta: Texto de la etiqueta (se convierte a mayúsculas)
        valor: Valor a mostrar
        ancho: Ancho de la celda en mm
        alignment: Alineación del texto (TA_LEFT, TA_CENTER, TA_RIGHT)
        
    Returns:
        Tabla con la celda formateada
    """
    valor_str = str(valor) if valor not in (None, '', 'None') else '—'
    
    # Determinar si el valor debe estar en negrita (para campos pequeños)
    bold = etiqueta.upper() in ('SEXO', 'EDAD', 'CONDICIÓN', 'NO. HOJA')
    
    # Crear párrafos con la alineación especificada
    etiqueta_para = Paragraph(etiqueta.upper(), _estilo_etiqueta(7 if not bold else 6, alignment))
    valor_para = Paragraph(valor_str, _estilo_valor(9, bold=bold, alignment=alignment))
    
    celda = Table(
        [
            [etiqueta_para],
            [valor_para],
        ],
        colWidths=[ancho],
        rowHeights=[ALTURA_FILA_ETIQUETA, ALTURA_FILA_VALOR],
    )
    
    # Estilo de la celda (sin incluir ALIGN adicional)
    celda.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), VERDE_MUY_CLARO),
        ('BACKGROUND', (0, 1), (-1, 1), BLANCO),
        ('BOX', (0, 0), (-1, -1), 0.5, VERDE_CLARO),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, VERDE_CLARO),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    return celda


# ═══════════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL - SECCIÓN A
# ═══════════════════════════════════════════════════════════════════════════════
class SeccionAEstablecimientoPaciente(BaseSeccion):
    """
    Sección A del Formulario 033: DATOS DE ESTABLECIMIENTO Y USUARIO / PACIENTE
    
    Genera una UI unificada con color verde médico que incluye:
    - Fila A: Datos del establecimiento de salud
    - Fila B: Datos del paciente
    
    Diseño: Profesional, compacto, con todos los campos del formulario oficial.
    """
    
    nombre_seccion = 'A. Datos de Establecimiento y Usuario / Paciente'
    es_opcional = False  # Siempre debe aparecer
    
    def construir(self, historial) -> List[Flowable]:
        """
        Construye la sección completa A en una sola UI.
        
        Args:
            historial: Instancia de ClinicalRecord
            
        Returns:
            Lista de elementos Flowable
        """
        elementos = []
        
        # ═══════════════════════════════════════════════════════════════════════
        # ENCABEZADO DE LA SECCIÓN
        # ═══════════════════════════════════════════════════════════════════════
        titulo = Table(
            [[Paragraph(
                'A. DATOS DE ESTABLECIMIENTO Y USUARIO / PACIENTE',
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # FILA A: DATOS DEL ESTABLECIMIENTO
        # ═══════════════════════════════════════════════════════════════════════
        fila_establecimiento = self._construir_fila_establecimiento(historial)
        elementos.append(fila_establecimiento)
        
        # ═══════════════════════════════════════════════════════════════════════
        # FILA B: DATOS DEL PACIENTE
        # ═══════════════════════════════════════════════════════════════════════
        fila_paciente = self._construir_fila_paciente(historial)
        elementos.append(fila_paciente)
        
        # Espaciado final
        elementos.append(Spacer(1, 8))
        
        return elementos
    
    def _construir_fila_establecimiento(self, historial) -> Table:
        """
        Construye la FILA A: Datos del establecimiento.
        
        Campos:
        - INSTITUCIÓN DEL SISTEMA
        - UNICÓDIGO
        - ESTABLECIMIENTO DE SALUD
        - NÚMERO DE ARCHIVO
        - No. HOJA
        
        Returns:
            Tabla con la fila completa
        """
        # Anchos de columna para cada campo (5 columnas)
        total_ancho = ANCHO_PAGINA  # ~170mm
        
        # Distribuir el ancho entre 5 columnas
        w_institucion = 50 * mm
        w_unicodigo = 25 * mm
        w_establecimiento = 45 * mm
        w_archivo = 25 * mm
        w_hoja = 25 * mm
        
        # Verificar que la suma no exceda el ancho total
        suma_anchos = w_institucion + w_unicodigo + w_establecimiento + w_archivo + w_hoja
        if suma_anchos > total_ancho:
            # Ajustar proporcionalmente
            factor = total_ancho / suma_anchos
            w_institucion *= factor
            w_unicodigo *= factor
            w_establecimiento *= factor
            w_archivo *= factor
            w_hoja *= factor
        
        # Obtener valores del historial
        institucion = historial.institucion_sistema or 'SISTEMA NACIONAL DE SALUD'
        unicodigo = historial.unicodigo or '—'
        establecimiento = historial.establecimiento_salud or '—'
        numero_archivo = historial.numero_archivo or '—'
        numero_hoja = str(historial.numero_hoja) if historial.numero_hoja else '1'
        
        # Crear celdas individuales usando la función unificada
        fila = Table(
            [[
                _crear_celda('Institución del Sistema', institucion, w_institucion, TA_LEFT),
                _crear_celda('Unicódigo', unicodigo, w_unicodigo, TA_CENTER),
                _crear_celda('Establecimiento de Salud', establecimiento, w_establecimiento, TA_LEFT),
                _crear_celda('No. Archivo', numero_archivo, w_archivo, TA_CENTER),
                _crear_celda('No. Hoja', numero_hoja, w_hoja, TA_CENTER),
            ]],
            colWidths=[w_institucion, w_unicodigo, w_establecimiento, w_archivo, w_hoja],
        )
        
        # Establecer altura uniforme para toda la fila
        fila.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        return fila
    
    def _construir_fila_paciente(self, historial) -> Table:
        """
        Construye la FILA B: Datos del paciente.
        
        Campos:
        - APELLIDO
        - NOMBRE
        - SEXO
        - EDAD
        - CONDICIÓN EDAD (H/D/M/A)
        
        Returns:
            Tabla con la fila completa
        """
        paciente = historial.paciente
        
        # Anchos de columna - 5 columnas
        total_ancho = ANCHO_PAGINA  # ~170mm
        w_apellido = 55 * mm        # Ancho para Apellido
        w_nombre = 55 * mm           # Ancho para Nombre
        w_sexo = 20 * mm             # Ancho para Sexo
        w_edad = 20 * mm             # Ancho para Edad
        w_condicion = 20 * mm        # Ancho para Condición
        
        # Verificar que la suma no exceda el ancho total
        suma_anchos = w_apellido + w_nombre + w_sexo + w_edad + w_condicion
        if suma_anchos > total_ancho:
            # Ajustar proporcionalmente
            factor = total_ancho / suma_anchos
            w_apellido *= factor
            w_nombre *= factor
            w_sexo *= factor
            w_edad *= factor
            w_condicion *= factor
        
        # Extraer datos del paciente
        nombres_lista = (paciente.nombres or '').split()
        apellidos_lista = (paciente.apellidos or '').split()
        
        # Combinar apellidos y nombres
        apellido_completo = ' '.join(apellidos_lista) if apellidos_lista else '—'
        nombre_completo = ' '.join(nombres_lista) if nombres_lista else '—'
        
        # Sexo
        sexo_display = self._formatear_sexo(paciente.sexo)
        
        # Edad y condición
        edad, condicion = self._calcular_edad_condicion(paciente.fecha_nacimiento)
        
        # Crear celdas usando la función unificada
        fila = Table(
            [[
                _crear_celda('Apellido', apellido_completo, w_apellido, TA_LEFT),
                _crear_celda('Nombre', nombre_completo, w_nombre, TA_LEFT),
                _crear_celda('Sexo', sexo_display, w_sexo, TA_CENTER),
                _crear_celda('Edad', edad, w_edad, TA_CENTER),
                _crear_celda('Condición', condicion, w_condicion, TA_CENTER),
            ]],
            colWidths=[w_apellido, w_nombre, w_sexo, w_edad, w_condicion],
        )
        
        # Establecer altura uniforme para toda la fila
        fila.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        return fila
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTODOS AUXILIARES
    # ═══════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def _formatear_sexo(sexo):
        """
        Formatea el sexo para mostrar.
        
        Args:
            sexo: 'M', 'F', 'Masculino', 'Femenino', etc.
            
        Returns:
            'M' o 'F' o '—'
        """
        if not sexo:
            return '—'
        
        sexo_str = str(sexo).upper().strip()
        
        if sexo_str in ('M', 'MASCULINO', 'HOMBRE', 'MALE'):
            return 'M'
        elif sexo_str in ('F', 'FEMENINO', 'MUJER', 'FEMALE'):
            return 'F'
        else:
            return sexo_str[:1] if sexo_str else '—'
    
    @staticmethod
    def _calcular_edad_condicion(fecha_nacimiento):
        """
        Calcula la edad y determina la condición (H/D/M/A).
        
        Condiciones:
        - H: Horas (< 24 horas)
        - D: Días (< 30 días)
        - M: Meses (< 12 meses)
        - A: Años (>= 12 meses)
        
        Args:
            fecha_nacimiento: Date object
            
        Returns:
            Tupla (edad_str, condicion_str)
            Ejemplo: ('25', 'A') o ('6', 'M') o ('15', 'D')
        """
        if not fecha_nacimiento:
            return ('—', '—')
        
        try:
            hoy = datetime.now().date()
            diferencia = hoy - fecha_nacimiento
            dias_totales = diferencia.days
            
            # Horas (menos de 1 día)
            if dias_totales < 1:
                horas = diferencia.total_seconds() / 3600
                return (f'{int(horas)}', 'H')
            
            # Días (menos de 30 días)
            if dias_totales < 30:
                return (f'{dias_totales}', 'D')
            
            # Meses (menos de 365 días / ~12 meses)
            if dias_totales < 365:
                meses = dias_totales // 30
                return (f'{meses}', 'M')
            
            # Años
            anios = dias_totales // 365
            return (f'{anios}', 'A')
            
        except Exception:
            return ('—', '—')


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionAEstablecimientoPaciente']