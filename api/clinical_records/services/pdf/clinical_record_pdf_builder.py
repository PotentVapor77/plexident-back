# api/clinical_records/services/pdf/clinical_record_pdf_builder.py
"""
Builder principal del PDF del historial clínico.

USO BÁSICO:
    from api.clinical_records.services.pdf.clinical_record_pdf_builder import (
        ClinicalRecordPDFBuilder
    )

    # Generar todas las secciones disponibles
    pdf_bytes = ClinicalRecordPDFBuilder.generar(historial)

    # Generar solo secciones específicas
    pdf_bytes = ClinicalRecordPDFBuilder.generar(
        historial,
        secciones=['datos_paciente', 'constantes_vitales', 'plan_tratamiento']
    )

AGREGAR UNA NUEVA SECCIÓN:
    1. Crear clase en secciones.py que herede de BaseSeccion
    2. Añadirla a SECCIONES_DISPONIBLES con una clave de string
    3. Listo: estará disponible automáticamente
"""
import io
import logging
import os
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from api.clinical_records.services.pdf.sections.seccion_a_establecimiento_paciente import SeccionAEstablecimientoPaciente
from api.clinical_records.services.pdf.sections.seccion_b_motivo_consulta import SeccionBMotivoConsulta
from api.clinical_records.services.pdf.sections.seccion_c_enfermedad_actual import SeccionCEnfermedadActual
from api.clinical_records.services.pdf.sections.seccion_d_antecedentes_personales import SeccionDAntecedentesPersonales
from api.clinical_records.services.pdf.sections.seccion_e_antecedentes_familiares import SeccionEAntecedentesFamiliares
from api.clinical_records.services.pdf.sections.seccion_f_constantes_vitales import SeccionFConstantesVitales
from api.clinical_records.services.pdf.sections.seccion_g_examen_estomatognatico import SeccionGExamenEstomatognatico
from api.clinical_records.services.pdf.sections.seccion_h_odontograma import SeccionHOdontograma
from api.clinical_records.services.pdf.sections.seccion_i_indicadores_salud_bucal import SeccionIIndicadoresSaludBucal
from api.clinical_records.services.pdf.sections.seccion_j_indices_cpo_ceo import SeccionJIndicesCPOceo

from .sections.base_section import COLOR_BORDE, COLOR_PRIMARIO, COLOR_SECUNDARIO, COLOR_SUBTEXTO, ESTILOS
from .sections.secciones import (
    SeccionEstablecimientoPaciente,
    SeccionMotivoConsulta,
    SeccionConstantesVitales,
    SeccionAntecedentesPersonales,
    SeccionAntecedentesFamiliares,
    SeccionPlanTratamiento,
    SeccionIndicadoresSaludBucal,
    SeccionIndicesCaries,
    SeccionDiagnosticosCIE,
    SeccionExamenesComplementarios,
    SeccionObservaciones,
)

logger = logging.getLogger(__name__)

# Ruta del logo
RUTA_LOGO = os.path.join(os.path.dirname(__file__), 'src', 'logo.png')


class ClinicalRecordPDFBuilder:
    """
    Orquestador del PDF del historial clínico.

    SECCIONES_DISPONIBLES define el orden y la clave de cada sección.
    Para activar/desactivar secciones sin tocar la lógica de generación,
    simplemente pasa el parámetro `secciones` al llamar a `generar()`.
    """

    # ── Registro de secciones ──────────────────────────────────────────────
    # El orden aquí es el orden en que aparecen en el PDF.
    # Clave (str) → Clase de sección
    SECCIONES_DISPONIBLES = {
        'establecimiento_paciente': SeccionAEstablecimientoPaciente,
        'motivo_consulta': SeccionBMotivoConsulta,

        'enfermedad_actual': SeccionCEnfermedadActual,
        'antecedentes_personales': SeccionDAntecedentesPersonales,
        'antecedentes_familiares': SeccionEAntecedentesFamiliares,
        'constantes_vitales': SeccionFConstantesVitales,
        'examen_estomatognatico': SeccionGExamenEstomatognatico,
        'odontograma': SeccionHOdontograma,
        'indicadores_salud_bucal':   SeccionIIndicadoresSaludBucal,   
        'indices_caries':            SeccionJIndicesCPOceo,            
        'plan_tratamiento':          SeccionPlanTratamiento,
        'diagnosticos_cie':          SeccionDiagnosticosCIE,
        'examenes_complementarios':  SeccionExamenesComplementarios,
        'observaciones':             SeccionObservaciones,
    }

    @classmethod
    def generar(
        cls,
        historial,
        secciones: Optional[List[str]] = None,
    ) -> bytes:
        """
        Genera el PDF y retorna los bytes listos para servir como HttpResponse.

        Args:
            historial:  Instancia de ClinicalRecord (ya con relaciones cargadas).
            secciones:  Lista de claves de SECCIONES_DISPONIBLES a incluir.
                        Si es None, se incluyen todas.

        Returns:
            bytes del PDF generado.
        """
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=25 * mm,  # Aumentado para dar espacio al logo
            bottomMargin=20 * mm,
            title=f"Historia Clínica {historial.numero_historia_clinica_unica or ''}",
            author='Sistema Odontológico',
        )

        story = cls._construir_story(historial, secciones)

        doc.build(
            story,
            onFirstPage=cls._pie_pagina,
            onLaterPages=cls._pie_pagina,
        )

        buffer.seek(0)
        return buffer.read()

    @classmethod
    def _construir_story(cls, historial, secciones: Optional[List[str]]) -> list:
        """Construye la lista de elementos (story) del PDF."""
        story = []

        # Agregar encabezado con logo
        story.extend(cls._encabezado_logo(historial))

        # Determinar qué secciones generar y en qué orden
        claves = secciones if secciones else list(cls.SECCIONES_DISPONIBLES.keys())

        # Validar claves desconocidas
        invalidas = [k for k in claves if k not in cls.SECCIONES_DISPONIBLES]
        if invalidas:
            logger.warning(f"Secciones desconocidas ignoradas: {invalidas}")
            claves = [k for k in claves if k in cls.SECCIONES_DISPONIBLES]

        for clave in claves:
            clase_seccion = cls.SECCIONES_DISPONIBLES[clave]
            seccion = clase_seccion()

            try:
                elementos = seccion.construir(historial)
                if elementos:
                    story.extend(elementos)
            except Exception as e:
                logger.error(
                    f"Error construyendo sección '{clave}' "
                    f"para historial {historial.id}: {e}",
                    exc_info=True,
                )
                # Agregar bloque de error no bloqueante
                story.append(cls._bloque_error_seccion(seccion.nombre_seccion))

        # Firma al final
        story.extend(cls._firma(historial))
        return story

    @classmethod
    def _encabezado_logo(cls, historial) -> list:
        """
        Crea el encabezado con logo y título del documento.
        """
        elementos = []

        # Intentar cargar el logo
        try:
            if os.path.exists(RUTA_LOGO):
                logo = Image(RUTA_LOGO)
                logo.drawHeight = 15 * mm
                logo.drawWidth = 40 * mm
            else:
                # Fallback si no existe el logo
                logo = Paragraph("FamysALUD<br/>CENTROMEDICO", ParagraphStyle(
                    'LogoFallback',
                    fontSize=14,
                    fontName='Helvetica-Bold',
                    textColor=COLOR_PRIMARIO,
                    alignment=TA_LEFT,
                ))
        except Exception as e:
            logger.warning(f"No se pudo cargar el logo: {e}")
            logo = Paragraph("FamysALUD<br/>CENTROMEDICO", ParagraphStyle(
                'LogoFallback',
                fontSize=14,
                fontName='Helvetica-Bold',
                textColor=COLOR_PRIMARIO,
                alignment=TA_LEFT,
            ))

        # Crear tabla de encabezado con 3 columnas: logo, título, fecha/HC
        estilo_titulo = ParagraphStyle(
            'TituloDocumento',
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=COLOR_PRIMARIO,
            alignment=TA_CENTER,
            leading=16,
        )

        estilo_info = ParagraphStyle(
            'InfoDocumento',
            fontSize=8,
            fontName='Helvetica',
            textColor=COLOR_SUBTEXTO,
            alignment=TA_RIGHT,
            leading=10,
        )

        # Información de la derecha
        fecha_atencion = str(historial.fecha_atencion)[:10] if historial.fecha_atencion else '—'
        info_derecha = f"""<b>H.C. Única:</b> {historial.numero_historia_clinica_unica or '—'}<br/>
<b>Fecha Atención:</b> {fecha_atencion}<br/>
<b>Documento:</b> Formulario 033"""

        encabezado = Table(
            [[
                logo,
                Paragraph("HISTORIA CLÍNICA ODONTOLÓGICA<br/><font size=10>Registro de Atención</font>", estilo_titulo),
                Paragraph(info_derecha, estilo_info),
            ]],
            colWidths=[50 * mm, 70 * mm, 50 * mm],
        )

        encabezado.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        elementos.append(encabezado)

        # Línea decorativa
        elementos.append(HRFlowable(
            width='100%',
            thickness=1,
            color=COLOR_SECUNDARIO,
            spaceBefore=2,
            spaceAfter=8,
        ))

        return elementos

    @classmethod
    def _bloque_error_seccion(cls, nombre: str):
        """Bloque de fallback cuando una sección lanza excepción."""
        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import ParagraphStyle
        estilo = ParagraphStyle(
            'Error', fontSize=8, textColor=colors.HexColor('#922B21'),
            fontName='Helvetica-Oblique',
        )
        return Paragraph(f"[Error al generar sección: {nombre}]", estilo)

    @staticmethod
    def _firma(historial) -> list:
        """Bloque de firma del odontólogo al final del documento."""
        od = historial.odontologo_responsable
        nombre_od = '—'
        if od:
            nombre_od = f"{getattr(od, 'nombres', '')} {getattr(od, 'apellidos', '')}".strip()

        estilo_firma = ParagraphStyle(
            'Firma', fontSize=8, alignment=TA_CENTER,
            textColor=COLOR_SUBTEXTO,
        )

        linea = Table(
            [['', '']],
            colWidths=[80 * mm, 80 * mm],
        )
        linea.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (0, 0), 0.5, COLOR_PRIMARIO),
            ('LINEABOVE', (1, 0), (1, 0), 0.5, COLOR_PRIMARIO),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ]))

        return [
            Spacer(1, 14),
            HRFlowable(width='100%', thickness=0.5, color=COLOR_BORDE),
            Spacer(1, 8),
            linea,
            Paragraph(f"Firma Odontólogo: {nombre_od}", estilo_firma),
            Spacer(1, 4),
            Paragraph(
                f"Generado el: "
                f"{str(historial.fecha_atencion)[:10] if historial.fecha_atencion else '—'}",
                estilo_firma,
            ),
        ]

    @staticmethod
    def _pie_pagina(canvas, doc):
        """Pie de página con número de página y número de HC."""
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(COLOR_SUBTEXTO)

        ancho, alto = A4
        y = 12 * mm

        # Izquierda: nombre del sistema
        canvas.drawString(20 * mm, y, 'FamysALUD CENTROMEDICO — Formulario 033')

        # Centro: número de HC
        hc = getattr(doc, 'title', '')
        canvas.drawCentredString(ancho / 2, y, hc)

        # Derecha: número de página
        canvas.drawRightString(
            ancho - 20 * mm, y,
            f"Pág. {canvas.getPageNumber()}"
        )
        canvas.restoreState()

    @classmethod
    def secciones_disponibles(cls) -> dict:
        """Retorna el catálogo de secciones con su nombre legible."""
        return {
            clave: clase().nombre_seccion
            for clave, clase in cls.SECCIONES_DISPONIBLES.items()
        }