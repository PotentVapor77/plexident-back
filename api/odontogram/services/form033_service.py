# api/odontogram/services/form033_service.py

import logging
from uuid import UUID
from datetime import datetime
from typing import Dict, List, Optional, Any

from django.db.models import Q, Prefetch
from django.utils import timezone

from api.patients.models import Paciente
from api.odontogram.models import Diente, DiagnosticoDental, Diagnostico

logger = logging.getLogger(__name__)


class Form033Service:
    """Servicio para exportación a Formulario 033"""

    # Mapeo de símbolos formulario 033
    SIMBOLO_MAPPING = {
        # ============ SELLANTES ============
        "U_rojo": {
            "simbolo": "Ü",
            "color": "#FF0000",
            "descripcion": "Sellante necesario",
            "categoria": "rojo",
            "tipo": "preventivo_indicado",
        },
        "U_azul": {
            "simbolo": "Ü",
            "color": "#0000FF",
            "descripcion": "Sellante realizado",
            "categoria": "azul",
            "tipo": "preventivo_realizado",
        },
        # ============ EXTRACCIONES / PÉRDIDAS ============
        "X_rojo": {
            "simbolo": "X",
            "color": "#FF0000",
            "descripcion": "Extracción indicada",
            "categoria": "rojo",
            "tipo": "extraccion_indicada",
        },
        "X_azul": {
            "simbolo": "X",
            "color": "#0000FF",
            "descripcion": "Pérdida por caries",
            "categoria": "azul",
            "tipo": "perdido",
        },
        "_azul": {
            "simbolo": "|",
            "color": "#0000FF",
            "descripcion": "Pérdida (otra causa)",
            "categoria": "rojo",
            "tipo": "perdido_otra_causa",
        },
        # ============ ENDODONCIA ============
        "r": {
            "simbolo": "r",
            "color": "#FF0000",
            "descripcion": "Endodoncia por realizar",
            "categoria": "rojo",
            "tipo": "endodoncia_indicada",
        },
        "_azul": {
            "simbolo": "|",
            "color": "#0000FF",
            "descripcion": "Endodoncia realizada",
            "categoria": "azul",
            "tipo": "endodoncia_realizada",
        },
        # ============ CARIES / OBTURACIÓN ============
        "O_rojo": {
            "simbolo": "O",
            "color": "#FF0000",
            "descripcion": "Caries",
            "categoria": "rojo",
            "tipo": "patologia",
        },
        "o_azul": {
            "simbolo": "o",
            "color": "#0000FF",
            "descripcion": "Obturado",
            "categoria": "azul",
            "tipo": "restaurado",
        },
        # ============ AUSENTE ============
        "A": {
            "simbolo": "A",
            "color": "#000000",
            "descripcion": "Ausente",
            "categoria": "negro",
            "tipo": "ausente",
        },
        # ============ PRÓTESIS FIJA ============
        "--": {
            "simbolo": "¨---¨",
            "color": "#FF0000",
            "descripcion": "Prótesis fija indicada",
            "categoria": "rojo",
            "tipo": "protesis_indicada",
        },
        "--_azul": {
            "simbolo": "¨---¨",
            "color": "#0000FF",
            "descripcion": "Prótesis fija realizada",
            "categoria": "azul",
            "tipo": "protesis_realizada",
        },
        # ============ PRÓTESIS REMOVIBLE ============
        "-----": {
            "simbolo": "(-----)",
            "color": "#FF0000",
            "descripcion": "Prótesis removible indicada",
            "categoria": "rojo",
            "tipo": "protesis_indicada",
        },
        "----_azul": {
            "simbolo": "(-----)",
            "color": "#0000FF",
            "descripcion": "Prótesis removible realizada",
            "categoria": "azul",
            "tipo": "protesis_realizada",
        },
        # ============ CORONA ============
        "ª": {
            "simbolo": "ª",
            "color": "#FF0000",
            "descripcion": "Corona indicada",
            "categoria": "rojo",
            "tipo": "corona_indicada",
        },
        "ª_azul": {
            "simbolo": "ª",
            "color": "#0000FF",
            "descripcion": "Corona realizada",
            "categoria": "azul",
            "tipo": "corona_realizada",
        },
        # ============ PRÓTESIS TOTAL ============
        "═": {
            "simbolo": "═",
            "color": "#FF0000",
            "descripcion": "Prótesis total indicada",
            "categoria": "rojo",
            "tipo": "protesis_total_indicada",
        },
        "═_azul": {
            "simbolo": "═",
            "color": "#0000FF",
            "descripcion": "Prótesis total realizada",
            "categoria": "azul",
            "tipo": "protesis_total_realizada",
        },
        # ============ SANO (Adicional) ============
        "check": {
            "simbolo": "✓",
            "color": "#00AA00",
            "descripcion": "Sano",
            "categoria": "verde",
            "tipo": "sano",
        },
    }

    # Mapeo FDI a posiciones tabla 4x8
    FDI_MAPPING = {
        # Dientes Permanentes
        # Superior Derecho (18-11)
        "18": {"cuadrante": "superior_derecho", "posicion": 0},
        "17": {"cuadrante": "superior_derecho", "posicion": 1},
        "16": {"cuadrante": "superior_derecho", "posicion": 2},
        "15": {"cuadrante": "superior_derecho", "posicion": 3},
        "14": {"cuadrante": "superior_derecho", "posicion": 4},
        "13": {"cuadrante": "superior_derecho", "posicion": 5},
        "12": {"cuadrante": "superior_derecho", "posicion": 6},
        "11": {"cuadrante": "superior_derecho", "posicion": 7},
        # Superior Izquierdo (21-28)
        "21": {"cuadrante": "superior_izquierdo", "posicion": 0},
        "22": {"cuadrante": "superior_izquierdo", "posicion": 1},
        "23": {"cuadrante": "superior_izquierdo", "posicion": 2},
        "24": {"cuadrante": "superior_izquierdo", "posicion": 3},
        "25": {"cuadrante": "superior_izquierdo", "posicion": 4},
        "26": {"cuadrante": "superior_izquierdo", "posicion": 5},
        "27": {"cuadrante": "superior_izquierdo", "posicion": 6},
        "28": {"cuadrante": "superior_izquierdo", "posicion": 7},
        # Inferior Izquierdo (31-38)
        "31": {"cuadrante": "inferior_izquierdo", "posicion": 0},
        "32": {"cuadrante": "inferior_izquierdo", "posicion": 1},
        "33": {"cuadrante": "inferior_izquierdo", "posicion": 2},
        "34": {"cuadrante": "inferior_izquierdo", "posicion": 3},
        "35": {"cuadrante": "inferior_izquierdo", "posicion": 4},
        "36": {"cuadrante": "inferior_izquierdo", "posicion": 5},
        "37": {"cuadrante": "inferior_izquierdo", "posicion": 6},
        "38": {"cuadrante": "inferior_izquierdo", "posicion": 7},
        # Inferior Derecho (41-48)
        "41": {"cuadrante": "inferior_derecho", "posicion": 0},
        "42": {"cuadrante": "inferior_derecho", "posicion": 1},
        "43": {"cuadrante": "inferior_derecho", "posicion": 2},
        "44": {"cuadrante": "inferior_derecho", "posicion": 3},
        "45": {"cuadrante": "inferior_derecho", "posicion": 4},
        "46": {"cuadrante": "inferior_derecho", "posicion": 5},
        "47": {"cuadrante": "inferior_derecho", "posicion": 6},
        "48": {"cuadrante": "inferior_derecho", "posicion": 7},
        # Dientes temporales
        # Superior Derecho (51-55)
        "51": {"cuadrante": "superior_derecho", "posicion": 0},
        "52": {"cuadrante": "superior_derecho", "posicion": 1},
        "53": {"cuadrante": "superior_derecho", "posicion": 2},
        "54": {"cuadrante": "superior_derecho", "posicion": 3},
        "55": {"cuadrante": "superior_derecho", "posicion": 4},
        # Superior Izquierdo (61-65)
        "61": {"cuadrante": "superior_izquierdo", "posicion": 0},
        "62": {"cuadrante": "superior_izquierdo", "posicion": 1},
        "63": {"cuadrante": "superior_izquierdo", "posicion": 2},
        "64": {"cuadrante": "superior_izquierdo", "posicion": 3},
        "65": {"cuadrante": "superior_izquierdo", "posicion": 4},
        # Inferior Izquierdo (71-75)
        "71": {"cuadrante": "inferior_izquierdo", "posicion": 0},
        "72": {"cuadrante": "inferior_izquierdo", "posicion": 1},
        "73": {"cuadrante": "inferior_izquierdo", "posicion": 2},
        "74": {"cuadrante": "inferior_izquierdo", "posicion": 3},
        "75": {"cuadrante": "inferior_izquierdo", "posicion": 4},
        # Inferior Derecho (81-85)
        "81": {"cuadrante": "inferior_derecho", "posicion": 0},
        "82": {"cuadrante": "inferior_derecho", "posicion": 1},
        "83": {"cuadrante": "inferior_derecho", "posicion": 2},
        "84": {"cuadrante": "inferior_derecho", "posicion": 3},
        "85": {"cuadrante": "inferior_derecho", "posicion": 4},
    }

    def generar_datos_form033(self, paciente_id: str) -> Dict[str, Any]:
        """
        Genera estructura JSON completa para Form 033

        Args:
            paciente_id: UUID del paciente

        Returns:
            Dict con estructura Form 033
        """
        try:
            paciente = Paciente.objects.get(id=UUID(paciente_id))
        except (Paciente.DoesNotExist, ValueError) as e:
            logger.error(f"Paciente no encontrado: {paciente_id}")
            raise ValueError(f"Paciente no encontrado: {paciente_id}") from e

        # Obtener dientes con diagnósticos
        dientes = (
            Diente.objects.filter(paciente=paciente)
            .select_related()
            .prefetch_related(
                Prefetch("superficies__diagnosticos__diagnostico_catalogo")
            )
        )

        # Construir tabla 4x8
        tabla = self._construir_tabla(dientes)

        # Calcular estadísticas
        stats = self._calcular_estadisticas(dientes)

        # Datos del paciente
        from datetime import date

        today = date.today()
        edad = (
            today.year - paciente.fecha_nacimiento.year
            if paciente.fecha_nacimiento
            else None
        )

        return {
            "seccion_i_paciente": {
                "cedula": paciente.cedula_pasaporte,
                "nombres": paciente.nombres,
                "apellidos": paciente.apellidos,
                "sexo": paciente.sexo,
                "edad": edad,
                "fecha_examen": today.isoformat(),
                "establecimiento": "Centro Medico FamySALUD",
                "provincia": "Guayas",
                "canton": "Guayaquil",
            },
            "seccion_ii_odontograma": tabla,
            "estadisticas": stats,
            "timestamp": datetime.now().isoformat(),
        }

    def obtener_simbolo_diente(self, diente: Diente) -> Dict[str, Any]:
        if diente.ausente:
            return self.SIMBOLO_MAPPING['A']
        
        # Obtener TODOS los diagnósticos ordenados por prioridad
        diagnosticos = DiagnosticoDental.objects.filter(
            superficie__diente=diente,
            activo=True
        ).select_related('diagnostico_catalogo').order_by(
            '-diagnostico_catalogo__prioridad',  # Mayor prioridad primero
            '-fecha'  # Más reciente primero
        )
        
        if diagnosticos.exists():
            diag_prioritario = diagnosticos.first()
            simbolo_key = diag_prioritario.diagnostico_catalogo.simbolo_formulario_033
            if simbolo_key in self.SIMBOLO_MAPPING:
                return self.SIMBOLO_MAPPING[simbolo_key]
    
        return self.SIMBOLO_MAPPING['check']  # Sano

    def _construir_tabla(self, dientes) -> Dict[str, List]:
        tabla = {
            "superior_derecho": [None] * 8,
            "superior_izquierdo": [None] * 8,
            "movilidad_superior_derecho": [None] * 8,
            "movilidad_superior_izquierdo": [None] * 8,
            "inferior_izquierdo": [None] * 8,
            "inferior_derecho": [None] * 8,
            "movilidad_inferior_derecho": [None] * 8,
            "movilidad_inferior_izquierdo": [None] * 8,
        }

        dientes_dict = {d.codigo_fdi: d for d in dientes}

        for fdi, diente in dientes_dict.items():
            mapping = self.FDI_MAPPING.get(fdi)
            if mapping:
                cuadrante = mapping["cuadrante"]
                posicion = mapping["posicion"]
                simbolo_info = self.obtener_simbolo_diente(diente)
                tabla[cuadrante][posicion] = simbolo_info

        return tabla

    def _calcular_estadisticas(self, dientes) -> Dict[str, int]:
        """
        Calcula estadísticas: sanos, cariados, perdidos, obturados, CPO-D

        Args:
            dientes: QuerySet de dientes

        Returns:
            Dict con estadísticas
        """
        stats = {
            "sanos": 0,
            "cariados": 0,
            "perdidos": 0,
            "obturados": 0,
            "cpod": 0,
        }

        for diente in dientes:
            if diente.ausente:
                stats["perdidos"] += 1
            else:
                simbolo_info = self.obtener_simbolo_diente(diente)

                if simbolo_info["simbolo"] == "X":
                    stats["cariados"] += 1
                elif simbolo_info["simbolo"] == "o":
                    stats["obturados"] += 1
                elif simbolo_info["simbolo"] == "✓":
                    stats["sanos"] += 1

        stats["cpod"] = stats["cariados"] + stats["perdidos"] + stats["obturados"]
        return stats

    def generar_html_form033(self, paciente_id: str) -> str:
        """
        Genera HTML visual para Form 033

        Args:
            paciente_id: UUID del paciente

        Returns:
            String HTML
        """
        datos = self.generar_datos_form033(paciente_id)
        paciente_data = datos["seccion_i_paciente"]
        tabla = datos["seccion_ii_odontograma"]
        stats = datos["estadisticas"]

        html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Formulario 033 - {paciente_data['nombres']}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            text-align: center;
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        .section {{
            margin: 20px 0;
            padding: 15px;
            background: #f9f9f9;
            border-left: 4px solid #007bff;
            border-radius: 4px;
        }}
        .section h2 {{
            margin-top: 0;
            color: #007bff;
        }}
        .patient-info {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}
        .info-item {{
            display: flex;
            justify-content: space-between;
        }}
        .info-label {{
            font-weight: bold;
            color: #666;
        }}
        .info-value {{
            color: #333;
        }}
        .odontogram {{
            margin: 20px 0;
            padding: 15px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .quadrant {{
            margin: 10px 0;
            padding: 10px;
            background: #f0f0f0;
            border-radius: 4px;
        }}
        .quadrant-title {{
            font-weight: bold;
            margin-bottom: 8px;
            color: #333;
        }}
        .tooth-row {{
            display: flex;
            gap: 8px;
            justify-content: space-around;
        }}
        .tooth {{
            width: 50px;
            height: 50px;
            border: 1px solid #ccc;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 18px;
            background: white;
        }}
        .tooth-healthy {{
            background: #90EE90;
            color: #333;
        }}
        .tooth-caries {{
            background: #FF6B6B;
            color: white;
        }}
        .tooth-absent {{
            background: #999;
            color: white;
        }}
        .tooth-filled {{
            background: #87CEEB;
            color: white;
        }}
        .statistics {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            margin: 15px 0;
        }}
        .stat-card {{
            background: white;
            border: 1px solid #ddd;
            padding: 10px;
            border-radius: 4px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        .cpod {{
            background: #fff3cd;
            border: 2px solid #ffc107;
            padding: 15px;
            border-radius: 4px;
            text-align: center;
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🦷 FORMULARIO 033 - ODONTOLOGÍA</h1>
        
        <div class="section">
            <h2>SECCIÓN I: DATOS DEL PACIENTE</h2>
            <div class="patient-info">
                <div class="info-item">
                    <span class="info-label">Cédula:</span>
                    <span class="info-value">{paciente_data['cedula']}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Nombres:</span>
                    <span class="info-value">{paciente_data['nombres']}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Apellidos:</span>
                    <span class="info-value">{paciente_data['apellidos']}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Sexo:</span>
                    <span class="info-value">{paciente_data['sexo']}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Edad:</span>
                    <span class="info-value">{paciente_data['edad']} años</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Fecha de Examen:</span>
                    <span class="info-value">{paciente_data['fecha_examen']}</span>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>SECCIÓN II: ODONTOGRAMA</h2>
            
            <div class="odontogram">
                <div class="quadrant">
                    <div class="quadrant-title">SUPERIOR DERECHO (18-11)</div>
                    <div class="tooth-row">
                        {self._generar_fila_html(tabla['superior_derecho'])}
                    </div>
                </div>
                
                <div class="quadrant">
                    <div class="quadrant-title">SUPERIOR IZQUIERDO (21-28)</div>
                    <div class="tooth-row">
                        {self._generar_fila_html(tabla['superior_izquierdo'])}
                    </div>
                </div>
                
                <div class="quadrant">
                    <div class="quadrant-title">INFERIOR IZQUIERDO (31-38)</div>
                    <div class="tooth-row">
                        {self._generar_fila_html(tabla['inferior_izquierdo'])}
                    </div>
                </div>
                
                <div class="quadrant">
                    <div class="quadrant-title">INFERIOR DERECHO (41-48)</div>
                    <div class="tooth-row">
                        {self._generar_fila_html(tabla['inferior_derecho'])}
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>ESTADÍSTICAS</h2>
            
            <div class="statistics">
                <div class="stat-card">
                    <div class="stat-value">{stats['sanos']}</div>
                    <div class="stat-label">Sanos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats['cariados']}</div>
                    <div class="stat-label">Cariados</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats['perdidos']}</div>
                    <div class="stat-label">Perdidos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats['obturados']}</div>
                    <div class="stat-label">Obturados</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats['cpod']}</div>
                    <div class="stat-label">CPO-D Total</div>
                </div>
            </div>
            
            <div class="cpod">
                📊 CPO-D: {stats['cpod']} / 32
            </div>
        </div>

        <div style="text-align: center; margin-top: 20px; color: #666; font-size: 12px;">
            <p>Generado: {datos['timestamp']}</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _generar_fila_html(self, fila_dientes: List) -> str:
        """
        Genera HTML para una fila de dientes

        Args:
            fila_dientes: Lista de símbolos de dientes

        Returns:
            String HTML
        """
        html_fila = ""
        for simbolo_info in fila_dientes:
            if not simbolo_info:
                html_fila += '<div class="tooth">-</div>'
            else:
                simbolo = simbolo_info["simbolo"]
                cat = simbolo_info["categoria"]

                if cat == "verde":
                    clase = "tooth-healthy"
                elif cat == "rojo":
                    clase = "tooth-caries"
                elif cat == "negro":
                    clase = "tooth-absent"
                elif cat == "azul":
                    clase = "tooth-filled"
                else:
                    clase = "tooth"

                html_fila += f'<div class="tooth {clase}">{simbolo}</div>'

        return html_fila
