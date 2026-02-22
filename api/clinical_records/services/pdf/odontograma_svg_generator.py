# api/clinical_records/services/pdf/odontograma_svg_generator.py
"""
Generador de odontograma 2D como SVG vectorial desde datos Form033.

"""
from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 
# ─────────────────────────────────────────────────────────────────────────────
TW      = 40
TH      = 40
GAP_H   = 3
META_H  = 14
BADGE_H = 13
ROW_GAP = 60                      
ARC_GAP = 50
SEP     = 10
PAD_X   = 18
PAD_Y   = 14
EXTRA_OFFSET_V = 5
# ─────────────────────────────────────────────────────────────────────────────
# PALETA
# ─────────────────────────────────────────────────────────────────────────────
C_CARIES       = "#E53E3E"
C_OBTURADO     = "#3182CE"
C_SANO         = "#38A169"
C_NEGRO        = "#1A202C"
C_GRIS         = "#718096"
C_BORDE        = "#CBD5E0"
C_CROWN_STROKE = "#4A5568"
C_CROWN_FILL   = "#FFFFFF"
C_BADGE_BG     = "#FFFFFF"
C_BADGE_FG     = "#1A202C"
C_MOV_BG       = "#FEFCBF"
C_MOV_FG       = "#744210"
C_MOV_BOR      = "#D97706"
C_REC_BG       = "#FFF5F5"
C_REC_FG       = "#9B2335"
C_REC_BOR      = "#FC8181"
C_EMPTY        = "#F7FAFC"
C_EMPTY_B      = "#E2E8F0"

_SURFACE_NORM: dict[str, str] = {
    # Nombres completos en español (Form033Service)
    "vestibular":    "V",
    "lingual":       "L",
    "oclusal":       "O",
    "distal":        "D",
    "mesial":        "M",
    # Con prefijo "cara_" (form033Adapter frontend)
    "cara_vestibular": "V",
    "cara_lingual":    "L",
    "cara_oclusal":    "O",
    "cara_distal":     "D",
    "cara_mesial":     "M",
    # Letras directas (compatibilidad hacia atrás)
    "v": "V",
    "l": "L",
    "o": "O",
    "d": "D",
    "m": "M",
    # Palatino = lingual para efectos visuales
    "palatino":      "L",
    "cara_palatino": "L",
}


def _normalize_surface(raw: str) -> str | None:
    """Convierte cualquier representación de superficie a la letra SVG (V/L/O/D/M).
    
    Retorna None si no se reconoce, para que se pueda filtrar.
    """
    return _SURFACE_NORM.get(raw.strip().lower())


_COLOR_MAP: dict[str, str] = {
    # Colores por nombre
    "red":      "#FF0000",
    "blue":     "#0000FF", 
    "green":    "#00FF00",
    "black":    "#000000",
    "gray":     "#718096",
    "white":    "#FFFFFF",
    "yellow":   "#FFFF00",
    "orange":   "#FFA500",
    "purple":   "#800080",
    
    # Colores por código hexadecimal 
    "#ff0000":  "#FF0000",
    "#f00":     "#FF0000",
    "#00ff00":  "#00FF00",
    "#0f0":     "#00FF00",
    "#0000ff":  "#0000FF",
    "#00f":     "#0000FF",
    "#000000":  "#000000",
    "#000":     "#000000",
    "#ffffff":  "#FFFFFF",
    "#fff":     "#FFFFFF",
    
    # Colores específicos del sistema
    "rojo":     "#FF0000",
    "azul":     "#0000FF",
    "verde":    "#00FF00",
    "negro":    "#000000",
}


def _resolve_color(raw: str | None, fallback: str = C_NEGRO) -> str:
    """Resuelve un color con logging para depuración."""
    if not raw:
        logger.debug(f"Color vacío, usando fallback: {fallback}")
        return fallback
    
    s = raw.strip().lower()
    
    logger.debug(f"Resolviendo color: original='{raw}', normalizado='{s}'")
    
    if s in _COLOR_MAP:
        result = _COLOR_MAP[s]
        logger.debug(f"Color encontrado en mapa: {s} -> {result}")
        return result
    
    if raw.strip().startswith("#"):
        logger.debug(f"Usando código hexadecimal directamente: {raw.strip()}")
        return raw.strip()
    
    for k, v in _COLOR_MAP.items():
        if k in s:
            logger.debug(f"Color encontrado por coincidencia parcial: '{k}' en '{s}' -> {v}")
            return v
    
    logger.warning(f"Color no reconocido: '{raw}', usando fallback: {fallback}")
    return fallback


# ─────────────────────────────────────────────────────────────────────────────
# MODO de renderizado por símbolo
# ─────────────────────────────────────────────────────────────────────────────
SIMBOLO_RENDER: dict[str, dict] = {
    "O":    {"mode": "surfaces"},
    "A":    {"mode": "text", "label": "A",   "fixed_color": "#000000", "bold": True,  "size": 15},  
    "✓":    {"mode": "text", "label": "✓",   "fixed_color": "#00AA00", "bold": True,  "size": 16},  
    "X":    {"mode": "text", "label": "✕",   "bold": True,  "size": 17}, 
    "Ü":    {"mode": "text", "label": "Ü",   "bold": False, "size": 16},
    "r":    {"mode": "text", "label": "r",   "bold": False, "size": 17},  
    "|":    {"mode": "text", "label": "|",   "bold": True,  "size": 19},  
    "ⓧ":   {"mode": "text", "label": "ⓧ",  "bold": False, "size": 15},  
    "ª":    {"mode": "text", "label": "ª",   "bold": False, "size": 16},  
    "═":    {"mode": "text", "label": "═",   "bold": False, "size": 15}, 
    "¨-¨":  {"mode": "text", "label": "¨-¨", "bold": False, "size": 18},  
    "(-)":  {"mode": "text", "label": "(-)", "bold": False, "size": 18},  
    "n":    {"mode": "text", "label": "n",   "bold": False, "size": 18},
    "3":    {"mode": "text", "label": "3",   "bold": True,  "size": 18},  
}

# ─────────────────────────────────────────────────────────────────────────────
# CUADRANTES (solo permanentes - ELIMINADO TEMPORAL)
# ─────────────────────────────────────────────────────────────────────────────
QUAD_PERM: list[dict] = [
    {"row": 0, "fdi_start": 11, "fdi_step": 1, "reverse": True, "side": "left", "upper": True},
    
    {"row": 1, "fdi_start": 21, "fdi_step": 1, "reverse": False, "side": "right", "upper": True},
    
    {"row": 2, "fdi_start": 31, "fdi_step": 1, "reverse": False, "side": "right", "upper": False},
    
    {"row": 3, "fdi_start": 41, "fdi_step": 1, "reverse": False, "side": "left", "upper": False},
]

# ─────────────────────────────────────────────────────────────────────────────
# PATHS 
# ─────────────────────────────────────────────────────────────────────────────

_PATH_OUTLINE = (
    "M 0.1524,0.1448 "
    "C 0.2441,0.0531 0.3710,0.0005 0.5007,0.0005 "
    "C 0.6304,0.0005 0.7573,0.0531 0.8490,0.1448 "
    "C 0.9473,0.2427 0.9998,0.3695 0.9998,0.4993 "
    "C 0.9998,0.6290 0.9473,0.7559 0.8490,0.8545 "
    "C 0.7573,0.9462 0.6304,0.9988 0.5007,0.9988 "
    "C 0.3710,0.9988 0.2441,0.9462 0.1524,0.8545 "
    "C 0.0533,0.7559 0.0007,0.6290 0.0007,0.4993 "
    "C 0.0007,0.3695 0.0533,0.2427 0.1524,0.1448 Z"
)

_SURFACE_PATHS: dict[str, str] = {

    "O": (
        "M 0.5007,0.2692 "
        "C 0.6244,0.2692 0.7308,0.3756 0.7308,0.4993 "
        "C 0.7308,0.6230 0.6244,0.7294 0.5007,0.7294 "
        "C 0.3769,0.7294 0.2706,0.6230 0.2706,0.4993 "
        "C 0.2706,0.3756 0.3769,0.2692 0.5007,0.2692 Z"
    ),

    # Vestibular: arco superior (clipPath 9f29bd315e)
    "V": (
        "M 0.1524,0.1448 "
        "C 0.2441,0.0531 0.3710,0.0005 0.5007,0.0005 "
        "C 0.6304,0.0005 0.7573,0.0531 0.8490,0.1448 "
        "L 0.6713,0.3225 "
        "C 0.6264,0.2776 0.5643,0.2518 0.5007,0.2518 "
        "C 0.4372,0.2518 0.3750,0.2776 0.3301,0.3225 Z"
    ),

    # Lingual: arco inferior (clipPath 37bb064443)
    "L": (
        "M 0.8490,0.8545 "
        "C 0.7573,0.9462 0.6304,0.9988 0.5007,0.9988 "
        "C 0.3710,0.9988 0.2441,0.9462 0.1524,0.8545 "
        "L 0.3301,0.6768 "
        "C 0.3750,0.7217 0.4372,0.7475 0.5007,0.7475 "
        "C 0.5643,0.7475 0.6264,0.7217 0.6713,0.6768 Z"
    ),

    # Distal: arco derecho (clipPath 5f820513ba)
    "D": (
        "M 0.8555,0.1509 "
        "C 0.9473,0.2427 0.9998,0.3695 0.9998,0.4993 "
        "C 0.9998,0.6290 0.9473,0.7559 0.8555,0.8476 "
        "L 0.6778,0.6699 "
        "C 0.7228,0.6249 0.7485,0.5628 0.7485,0.4993 "
        "C 0.7485,0.4357 0.7228,0.3736 0.6778,0.3286 Z"
    ),

    # Mesial: arco izquierdo (clipPath ace7745d03)
    "M": (
        "M 0.1450,0.8476 "
        "C 0.0533,0.7559 0.0007,0.6290 0.0007,0.4993 "
        "C 0.0007,0.3695 0.0533,0.2427 0.1450,0.1509 "
        "L 0.3227,0.3286 "
        "C 0.2778,0.3736 0.2520,0.4357 0.2520,0.4993 "
        "C 0.2520,0.5628 0.2778,0.6249 0.3227,0.6699 Z"
    ),
}


def _scale_path(norm_path: str, x: float, y: float, w: float, h: float) -> str:
    """
    Escala un path normalizado (0..1) a coordenadas absolutas SVG.
    Soporta comandos M, C, L, Z con valores "nx,ny".
    """
    tokens = norm_path.split()
    result: list[str] = []
    i = 0
    while i < len(tokens):
        cmd = tokens[i]
        if cmd in ("M", "L"):
            i += 1
            nx, ny = tokens[i].split(",")
            result.append(f"{cmd} {x + float(nx)*w:.3f},{y + float(ny)*h:.3f}")
        elif cmd == "C":
            pts: list[str] = []
            for _ in range(3):
                i += 1
                nx, ny = tokens[i].split(",")
                pts.append(f"{x + float(nx)*w:.3f},{y + float(ny)*h:.3f}")
            result.append(f"C {' '.join(pts)}")
        elif cmd == "Z":
            result.append("Z")
        i += 1
    return " ".join(result)


def _outline(x: float, y: float, w: float = TW, h: float = TH) -> str:
    return _scale_path(_PATH_OUTLINE, x, y, w, h)


def _surface(name: str, x: float, y: float) -> str:
    p = _SURFACE_PATHS.get(name, "")
    return _scale_path(p, x, y, TW, TH) if p else ""


# ─────────────────────────────────────────────────────────────────────────────
# Generador
# ─────────────────────────────────────────────────────────────────────────────

class OdontogramaSVGGenerator:

    @classmethod
    def generar_svg(cls, datos_form033: dict) -> str:
        odo_p = datos_form033.get("odontograma_permanente") or {}

        dp = odo_p.get("dientes",   [[], [], [], []])
        mp = odo_p.get("movilidad", [[], [], [], []])
        rp = odo_p.get("recesion",  [[], [], [], []])

        n       = 8
        half_w  = n * (TW + GAP_H)
        total_w = PAD_X * 2 + half_w * 2 + GAP_H * 2
        fila_h  = TH + BADGE_H + (META_H * 2) + 15
        arc_h   = (fila_h * 2) + ROW_GAP
        total_h = PAD_Y + 30 + arc_h + 40
        S = 4
        SEP = 10
        item_h = TH + SEP + BADGE_H + (META_H + S) * 2
        cx = total_w / 2
        y  = float(PAD_Y)
        out: list[str] = []

        out.append(f'<rect width="{total_w}" height="{total_h}" fill="white"/>')
        out.append(cls._txt(cx, y + 12,
            "ODONTOGRAMA – Formulario 033 MSP Ecuador",
            size=12, bold=True, anchor="middle"))
        y += 22

        out.extend(cls._arco("DENTICIÓN PERMANENTE", QUAD_PERM,
                              dp, mp, rp, total_w, cx, y, n))
        y += 16 + arc_h + ARC_GAP

        inner = "\n".join(out)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{total_w}" height="{total_h}" '
            f'viewBox="0 0 {total_w} {total_h}" '
            f'font-family="Helvetica,Arial,sans-serif">'
            f"{inner}</svg>"
        )

    @staticmethod
    def svg_a_png(svg_str: str, dpi: int = 150) -> bytes:
        svg_bytes = svg_str.encode("utf-8")

        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPM
            drawing = svg2rlg(io.BytesIO(svg_bytes))
            if drawing is None:
                raise ValueError("svg2rlg devolvió None")
            scale = dpi / 72.0
            drawing.width  *= scale
            drawing.height *= scale
            drawing.transform = (scale, 0, 0, scale, 0, 0)
            buf = io.BytesIO()
            renderPM.drawToFile(drawing, buf, fmt="PNG", dpi=dpi)
            buf.seek(0)
            return buf.read()
        except ImportError:
            logger.info("svglib no disponible, probando cairosvg…")
        except Exception as exc:
            logger.warning("svglib falló (%s), probando cairosvg…", exc)

        try:
            import cairosvg
            return cairosvg.svg2png(
                bytestring=svg_bytes, dpi=dpi, background_color="white")
        except ImportError:
            logger.info("cairosvg no disponible")
        except Exception as exc:
            logger.warning("cairosvg falló: %s", exc)

        raise RuntimeError("No se pudo generar el PNG. pip install svglib")

    # ── Arco ──────────────────────────────────────────────────────────────

    @classmethod
    def _arco(
        cls, titulo: str, quadrants: list[dict],
        dientes: list, movilidad: list, recesion: list,
        total_w: float, cx: float, y_start: float, n: int,
    ) -> list[str]:
        out: list[str] = []
        out.append(cls._txt(cx, y_start + 11, titulo,
                             size=9, bold=True, anchor="middle", color=C_GRIS))
        y0     = y_start + 16
        fila_h = META_H * 2 + BADGE_H + TH
        arc_h  = fila_h * 2 + ROW_GAP

        out.append(
            f'<line x1="{cx}" y1="{y0-2}" x2="{cx}" y2="{y0+arc_h-ROW_GAP+2}" '
            f'stroke="{C_BORDE}" stroke-width="1.5" stroke-dasharray="4,3"/>'
        )

        for q in quadrants:
            row      = q["row"]
            side     = q["side"]
            is_upper = q["upper"]

            d_row = list(dientes[row])   if row < len(dientes)   else []
            m_row = list(movilidad[row]) if row < len(movilidad) else []
            r_row = list(recesion[row])  if row < len(recesion)  else []

            if q["reverse"]:
                d_row.reverse(); m_row.reverse(); r_row.reverse()

            y_row = y0 if is_upper else y0 + fila_h + ROW_GAP

            for i in range(n):
                fdi   = q["fdi_start"] + q["fdi_step"] * i
                d     = d_row[i] if i < len(d_row) else None
                mov   = m_row[i] if i < len(m_row) else None
                rec   = r_row[i] if i < len(r_row) else None
                x_cell = (
                    cx - GAP_H - (i + 1) * (TW + GAP_H)
                    if side == "left"
                    else cx + GAP_H + i * (TW + GAP_H)
                )
                out.extend(cls._diente(d, mov, rec, x_cell, y_row, str(fdi), is_upper))

        return out

    # ── Diente individual ──────────────────────────────────────────────────

    @classmethod
    def _diente(
        cls,
        diente: dict | None,
        movilidad: dict | None,
        recesion:  dict | None,
        x: float,
        y_row: float,
        fdi: str,
        is_upper: bool,
    ) -> list[str]:
        out: list[str] = []
        cx = x + TW / 2
        
        # Separación entre elementos individuales
        S = 4  # gap entre rectángulos
        SEP = 10 # gap entre corona y rectángulos

        if is_upper:
            # Orden Superior (de arriba hacia abajo): Recesión -> Movilidad -> Badge -> [SEP] -> Corona
            y_rec   = y_row
            y_mov   = y_row + META_H + S
            y_badge = y_row + (META_H + S) + (META_H + S)
            y_crown = y_badge + BADGE_H + SEP 
        else:
            # Orden Inferior (de arriba hacia abajo): Corona -> [SEP] -> Badge -> Movilidad -> Recesión
            y_crown = y_row
            y_badge = y_row + TH + SEP
            y_mov   = y_badge + BADGE_H + S
            y_rec   = y_mov + META_H + S

        crown_outline = _outline(x, y_crown)

        # 1. Fondo blanco con la forma exacta del diente
        out.append(
            f'<path d="{crown_outline}" '
            f'fill="{C_CROWN_FILL}" stroke="none"/>'
        )

        # 2. Líneas de división de superficies (punteadas, muy finas)
        #    Periféricas primero
        for surf in ("V", "L", "D", "M"):
            sp = _surface(surf, x, y_crown)
            if sp:
                out.append(
                    f'<path d="{sp}" fill="none" '
                    f'stroke="{C_BORDE}" stroke-width="0.35" '
                    f'stroke-dasharray="1.2,1.2"/>'
                )
        # Oclusal encima
        sp_o = _surface("O", x, y_crown)
        if sp_o:
            out.append(
                f'<path d="{sp_o}" fill="none" '
                f'stroke="{C_BORDE}" stroke-width="0.35"/>'
            )

        # 3. Relleno de diagnóstico
        if diente:
            simbolo    = (diente.get("simbolo") or "").strip()
            diente_col = _resolve_color(diente.get("color", ""))
            # Normalizar superficies: del backend llegan en español
            # ("vestibular", "oclusal"…); los convertimos a letras SVG (V/L/O/D/M)
            raw_sups = diente.get("superficies_afectadas") or []
            sups = [
                norm
                for raw in raw_sups
                if (norm := _normalize_surface(raw)) is not None
            ]

            meta = SIMBOLO_RENDER.get(simbolo, {})
            # Activar modo superficies si:
            #   a) el símbolo está registrado como "surfaces" (ej: "O"), o
            #   b) hay superficies afectadas válidas aunque el símbolo sea otro
            #      (caries/obturación sin símbolo explícito, o símbolo "o" minúscula)
            mode = meta.get("mode", "text")
            if mode != "surfaces" and sups:
                mode = "surfaces"

            if mode == "surfaces" and sups:
                # Resolver el color UNA VEZ para todas las superficies
                diente_color = _resolve_color(diente.get("color", ""))
                logger.debug(
                    f"Renderizando superficies {sups} con color: {diente_color}"
                )
                # Periféricas primero (V, L, D, M), oclusal encima (O)
                for sup in [s for s in sups if s in ("V", "L", "D", "M")]:
                    sp = _surface(sup, x, y_crown)
                    if sp:
                        out.append(
                            f'<path d="{sp}" '
                            f'fill="{diente_color}" fill-opacity="0.72" '
                            f'stroke="{diente_color}" stroke-width="0.6"/>'
                        )
                if "O" in sups:
                    sp = _surface("O", x, y_crown)
                    if sp:
                        out.append(
                            f'<path d="{sp}" '
                            f'fill="{diente_color}" fill-opacity="0.72" '
                            f'stroke="{diente_color}" stroke-width="0.6"/>'
                        )
            else:
                # Modo texto: mostrar símbolo centrado en la corona
                label    = meta.get("label", simbolo) if meta else simbolo
                ov_color = meta.get("fixed_color", diente_col) if meta else diente_col
                bold     = meta.get("bold", False)
                size     = meta.get("size", 12)
                if label:   # no renderizar si no hay label (diente sin diagnóstico)
                    out.append(cls._txt(
                        cx, y_crown + TH * 0.54, label,
                        size=size, bold=bold, anchor="middle",
                        color=ov_color, dominant="middle",
                    ))

        # 4. Contorno exterior encima de todo (borde limpio)
        out.append(
            f'<path d="{crown_outline}" fill="none" '
            f'stroke="{C_CROWN_STROKE}" stroke-width="0.8"/>'
        )

        # 5. Badge FDI
        out.append(
            f'<rect x="{x+1}" y="{y_badge+1}" '
            f'width="{TW-2}" height="{BADGE_H-2}" '
            f'rx="2" fill="{C_BADGE_BG}" stroke="{C_BORDE}" stroke-width="0.5"/>'
        )
        out.append(cls._txt(
            cx, y_badge + BADGE_H / 2 + 1, fdi,
            size=8, bold=True, anchor="middle",
            color=C_BADGE_FG, dominant="middle",
        ))

        # 6. Movilidad
        if movilidad:
            grado = movilidad.get("grado", "")
            out.append(
                f'<rect x="{x+3}" y="{y_mov+1}" width="{TW-6}" height="{META_H-2}" '
                f'rx="2" fill="{C_MOV_BG}" stroke="{C_MOV_BOR}" stroke-width="0.5"/>'
            )
            out.append(cls._txt(
                cx, y_mov + META_H / 2 + 1, f"M{grado}",
                size=7, bold=True, anchor="middle",
                color=C_MOV_FG, dominant="middle",
            ))
        else:
            out.append(
                f'<rect x="{x+3}" y="{y_mov+1}" width="{TW-6}" height="{META_H-2}" '
                f'rx="2" fill="{C_EMPTY}" stroke="{C_EMPTY_B}" '
                f'stroke-width="0.4" stroke-dasharray="2,2"/>'
            )

        # 7. Recesión
        if recesion:
            nivel = recesion.get("nivel", "")
            out.append(
                f'<rect x="{x+3}" y="{y_rec+1}" width="{TW-6}" height="{META_H-2}" '
                f'rx="2" fill="{C_REC_BG}" stroke="{C_REC_BOR}" stroke-width="0.5"/>'
            )
            out.append(cls._txt(
                cx, y_rec + META_H / 2 + 1, f"R{nivel}",
                size=7, bold=True, anchor="middle",
                color=C_REC_FG, dominant="middle",
            ))
        else:
            out.append(
                f'<rect x="{x+3}" y="{y_rec+1}" width="{TW-6}" height="{META_H-2}" '
                f'rx="2" fill="{C_EMPTY}" stroke="{C_EMPTY_B}" '
                f'stroke-width="0.4" stroke-dasharray="2,2"/>'
            )

        return out

    # ── Helper texto ───────────────────────────────────────────────────────

    @staticmethod
    def _txt(
        x: float, y: float, label: str,
        size: float = 10,
        bold: bool = False,
        anchor: str = "start",
        color: str = C_NEGRO,
        dominant: str = "auto",
    ) -> str:
        fw   = "bold" if bold else "normal"
        safe = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return (
            f'<text x="{x:.1f}" y="{y:.1f}" '
            f'text-anchor="{anchor}" dominant-baseline="{dominant}" '
            f'font-size="{size}" font-weight="{fw}" fill="{color}">'
            f"{safe}</text>"
        )