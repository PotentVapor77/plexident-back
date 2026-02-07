# api/odontogram/services/form033_service.py

import logging
from uuid import UUID
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from collections import defaultdict

from django.db.models import Prefetch, Q

from api.patients.models import Paciente
from api.odontogram.models import (
    Diente, 
    DiagnosticoDental, 
    SuperficieDental,
    OpcionAtributoClinico
)

logger = logging.getLogger(__name__)


class Form033Service:
    """
    Servicio optimizado para exportación a Formulario 033 Ecuador
    Genera estructura de datos para odontograma 2D con:
    - 4 filas x 8 columnas (permanentes)
    - 4 filas x 5 columnas (temporales)
    - 2 filas adicionales: movilidad y recesión gingival
    """

    # ============================================================================
    # MAPEO DE SÍMBOLOS FORMULARIO 033 (con prioridad para conflictos)
    # ============================================================================
    
    SIMBOLO_MAPPING = {
        # ============ CARIES (Prioridad: 5 - CRÍTICA) ============
        "O_rojo": {
            "key": "caries",
            "simbolo": "O",
            "color": "#FF0000",
            "descripcion": "Caries",
            "categoria": "patologia_activa",
            "tipo": "patologia",
            "prioridad": 5,
        },
        
        # ============ PÉRDIDAS / AUSENCIAS (Prioridad: 5) ============
        "A": {
            "key": "ausente",
            "simbolo": "A",
            "color": "#000000",
            "descripcion": "Ausente",
            "categoria": "ausencia",
            "tipo": "ausente",
            "prioridad": 5,
        },
        "X_rojo": {
            "key": "extraccion_indicada",
            "simbolo": "X",
            "color": "#FF0000",
            "descripcion": "Extracción Indicada",
            "categoria": "patologia_activa",
            "tipo": "extraccion_indicada",
            "prioridad": 5,
        },
        "X_azul": {
            "key": "perdida_caries",
            "simbolo": "X",
            "color": "#0000FF",
            "descripcion": "Perdida por Caries",
            "categoria": "tratamiento_realizado",
            "tipo": "perdida_caries",
            "prioridad": 4,
        },
        "X_circulo_azul": {
            "key": "perdida_otra_causa",
            "simbolo": "ⓧ",
            "color": "#0000FF",
            "descripcion": "Perdida (otra causa)",
            "categoria": "tratamiento_realizado",
            "tipo": "perdida_otra_causa",
            "prioridad": 4,
        },
        
        "_rojo": {
            "key": "extraccion_otra_causa",
            "simbolo": "|",
            "color": "#FF0000",
            "descripcion": "Extracción (otra causa)",
            "categoria": "patologia_activa",
            "tipo": "extraccion_otra_causa",
            "prioridad": 4,
        },
        
        # ============ SELLANTES (Prioridad: 1-3) ============
        "U_rojo": {
            "key": "sellante_necesario",
            "simbolo": "Ü",
            "color": "#FF0000",
            "descripcion": "Sellante Necesario",
            "categoria": "patologia_activa",
            "tipo": "preventivo_indicado",
            "prioridad": 3,
        },
        "U_azul": {
            "key": "sellante_realizado",
            "simbolo": "Ü",
            "color": "#0000FF",
            "descripcion": "Sellante Realizado",
            "categoria": "tratamiento_realizado",
            "tipo": "preventivo_realizado",
            "prioridad": 2,
        },
        
        # ============ ENDODONCIA (Prioridad: 3-5) ============
        "r": {
            "key": "endodoncia_indicada",
            "simbolo": "r",
            "color": "#FF0000",
            "descripcion": "Endodoncia Por Realizar",
            "categoria": "patologia_activa",
            "tipo": "endodoncia_indicada",
            "prioridad": 5,
        },
        "_azul": {
            "key": "endodoncia_realizada",
            "simbolo": "|",
            "color": "#0000FF",
            "descripcion": "Endodoncia Realizada",
            "categoria": "tratamiento_realizado",
            "tipo": "endodoncia_realizada",
            "prioridad": 3,
        },
        
        # ============ OBTURACIONES (Prioridad: 2) ============
        "o_azul": {
            "key": "obturacion",
            "simbolo": "o",
            "color": "#0000FF",
            "descripcion": "Obturado",
            "categoria": "tratamiento_realizado",
            "tipo": "restaurado",
            "prioridad": 2,
        },
        
        # ============ CORONAS (Prioridad: 2-4) ============
        "ª": {
            "key": "corona_indicada",
            "simbolo": "ª",
            "color": "#FF0000",
            "descripcion": "Corona indicada",
            "categoria": "tratamiento_planificado",
            "tipo": "corona_indicada",
            "prioridad": 4,
        },
        "ª_azul": {
            "key": "corona_realizada",
            "simbolo": "ª",
            "color": "#0000FF",
            "descripcion": "Corona realizada",
            "categoria": "tratamiento_realizado",
            "tipo": "corona_realizada",
            "prioridad": 2,
        },
        
        # ============ PRÓTESIS FIJA (Prioridad: 2-4) ============
        "--": {
            "key": "protesis_fija_indicada",
            "simbolo": "¨-¨",
            "color": "#FF0000",
            "descripcion": "Prótesis fija indicada",
            "categoria": "tratamiento_planificado",
            "tipo": "protesis_indicada",
            "prioridad": 4,
        },
        "--_azul": {
            "key": "protesis_fija_realizada",
            "simbolo": "¨-¨",
            "color": "#0000FF",
            "descripcion": "Prótesis fija realizada",
            "categoria": "tratamiento_realizado",
            "tipo": "protesis_realizada",
            "prioridad": 2,
        },
        
        # ============ PRÓTESIS REMOVIBLE (Prioridad: 2-4) ============
        "-----": {
            "key": "protesis_removible_indicada",
            "simbolo": "(-)",
            "color": "#FF0000",
            "descripcion": "Prótesis removible indicada",
            "categoria": "tratamiento_planificado",
            "tipo": "protesis_indicada",
            "prioridad": 4,
        },
        "----_azul": {
            "key": "protesis_removible_realizada",
            "simbolo": "(-)",
            "color": "#0000FF",
            "descripcion": "Prótesis removible realizada",
            "categoria": "tratamiento_realizado",
            "tipo": "protesis_realizada",
            "prioridad": 2,
        },
        
        # ============ PRÓTESIS TOTAL (Prioridad: 2-4) ============
        "═": {
            "key": "protesis_total_indicada",
            "simbolo": "═",
            "color": "#FF0000",
            "descripcion": "Prótesis total indicada",
            "categoria": "tratamiento_planificado",
            "tipo": "protesis_total_indicada",
            "prioridad": 4,
        },
        "═_azul": {
            "key": "protesis_total_realizada",
            "simbolo": "═",
            "color": "#0000FF",
            "descripcion": "Prótesis total realizada",
            "categoria": "tratamiento_realizado",
            "tipo": "protesis_total_realizada",
            "prioridad": 2,
        },
        
        # ============ DIENTE SANO (Prioridad: 1) ============
        "check": {
            "key": "diente_sano",
            "simbolo": "✓",
            "color": "#00AA00",
            "descripcion": "Diente Sano",
            "categoria": "preventivo",
            "tipo": "sano",
            "prioridad": 1,
        },
    }

    # ============================================================================
    # MAPEO FDI A POSICIONES EN MATRIZ 4xN
    # ============================================================================
    
    # Permanentes: 4 filas x 8 columnas
    FDI_PERMANENTE = {
        # Superior Derecho (18-11) - Fila 0
        "18": (0, 0), "17": (0, 1), "16": (0, 2), "15": (0, 3),
        "14": (0, 4), "13": (0, 5), "12": (0, 6), "11": (0, 7),
        # Superior Izquierdo (21-28) - Fila 1
        "21": (1, 0), "22": (1, 1), "23": (1, 2), "24": (1, 3),
        "25": (1, 4), "26": (1, 5), "27": (1, 6), "28": (1, 7),
        # Inferior Izquierdo (31-38) - Fila 2
        "31": (2, 0), "32": (2, 1), "33": (2, 2), "34": (2, 3),
        "35": (2, 4), "36": (2, 5), "37": (2, 6), "38": (2, 7),
        # Inferior Derecho (41-48) - Fila 3
        "41": (3, 0), "42": (3, 1), "43": (3, 2), "44": (3, 3),
        "45": (3, 4), "46": (3, 5), "47": (3, 6), "48": (3, 7),
    }
    
    # Temporales: 4 filas x 5 columnas
    FDI_TEMPORAL = {
        # Superior Derecho (55-51) - Fila 0
        "55": (0, 0), "54": (0, 1), "53": (0, 2), "52": (0, 3), "51": (0, 4),
        # Superior Izquierdo (61-65) - Fila 1
        "61": (1, 0), "62": (1, 1), "63": (1, 2), "64": (1, 3), "65": (1, 4),
        # Inferior Izquierdo (71-75) - Fila 2
        "71": (2, 0), "72": (2, 1), "73": (2, 2), "74": (2, 3), "75": (2, 4),
        # Inferior Derecho (85-81) - Fila 3
        "85": (3, 0), "84": (3, 1), "83": (3, 2), "82": (3, 3), "81": (3, 4),
    }

    # ============================================================================
    # MÉTODO PRINCIPAL
    # ============================================================================
    
    def generar_datos_form033(self, paciente_id: str) -> Dict[str, Any]:
        """
        Genera estructura JSON completa para Form 033 Ecuador
        
        Returns:
            {
                "paciente": {...},
                "odontograma_permanente": {
                    "dientes": [[...], [...], [...], [...]],  # 4x8
                    "movilidad": [[...], [...], [...], [...]],
                    "recesion": [[...], [...], [...], [...]]
                },
                "odontograma_temporal": {
                    "dientes": [[...], [...], [...], [...]],  # 4x5
                    "movilidad": [[...], [...], [...], [...]],
                    "recesion": [[...], [...], [...], [...]]
                },
                "timestamp": "..."
            }
        """
        try:
            paciente = Paciente.objects.get(id=UUID(paciente_id))
        except (Paciente.DoesNotExist, ValueError) as e:
            # logger.error(f"[Form033] Paciente no encontrado: {paciente_id}")
            raise ValueError(f"Paciente no encontrado: {paciente_id}") from e

        # logger.info(f"[Form033] Generando datos para paciente {paciente.get_full_name()}")

        # Obtener dientes con prefetch optimizado
        dientes = self._obtener_dientes_optimizado(paciente)
        
        # Separar por dentición
        permanentes = [d for d in dientes if self._es_permanente(d.codigo_fdi)]
        temporales = [d for d in dientes if not self._es_permanente(d.codigo_fdi)]
        
        # logger.info(f"[Form033] Dientes permanentes: {len(permanentes)}, Temporales: {len(temporales)}")

        # Construir matrices
        odontograma_permanente = self._construir_matriz_permanente(permanentes)
        odontograma_temporal = self._construir_matriz_temporal(temporales)
        
        # Datos del paciente
        edad = self._calcular_edad(paciente.fecha_nacimiento) if paciente.fecha_nacimiento else None

        return {
            "paciente": {
                "cedula": paciente.cedula_pasaporte,
                "nombres": paciente.nombres,
                "apellidos": paciente.apellidos,
                "nombre_completo": paciente.get_full_name(),
                "sexo": paciente.sexo,
                "edad": edad,
                "fecha_nacimiento": paciente.fecha_nacimiento.isoformat() if paciente.fecha_nacimiento else None,
                "fecha_examen": date.today().isoformat(),
            },
            "odontograma_permanente": odontograma_permanente,
            "odontograma_temporal": odontograma_temporal,
            "timestamp": datetime.now().isoformat(),
        }

    # ============================================================================
    # MÉTODOS DE CONSTRUCCIÓN DE MATRICES
    # ============================================================================
    
    def _construir_matriz_permanente(self, dientes: List[Diente]) -> Dict[str, List[List]]:
        """
        Construye matriz 4x8 para dientes permanentes + movilidad + recesión
        """
        # Inicializar matrices vacías
        matriz_dientes = [[None] * 8 for _ in range(4)]
        matriz_movilidad = [[None] * 8 for _ in range(4)]
        matriz_recesion = [[None] * 8 for _ in range(4)]
        
        for diente in dientes:
            pos = self.FDI_PERMANENTE.get(diente.codigo_fdi)
            if not pos:
                continue
                
            fila, col = pos
            
            # Datos del diente (excluyendo movilidad/recesión)
            datos_diente = self._obtener_datos_diente(diente)
            matriz_dientes[fila][col] = datos_diente if datos_diente else None
            
            # Movilidad y recesión - SIEMPRE buscarlos (independientemente de datos_diente)
            matriz_movilidad[fila][col] = self._obtener_movilidad(diente)
            matriz_recesion[fila][col] = self._obtener_recesion(diente)
        
        return {
            "dientes": matriz_dientes,
            "movilidad": matriz_movilidad,
            "recesion": matriz_recesion,
        }
    def _construir_matriz_temporal(self, dientes: List[Diente]) -> Dict[str, List[List]]:
        """
        Construye matriz 4x5 para dientes temporales + movilidad + recesión
        """
        # Inicializar matrices vacías
        matriz_dientes = [[None] * 5 for _ in range(4)]
        matriz_movilidad = [[None] * 5 for _ in range(4)]
        matriz_recesion = [[None] * 5 for _ in range(4)]
        
        for diente in dientes:
            pos = self.FDI_TEMPORAL.get(diente.codigo_fdi)
            if not pos:
                continue
                
            fila, col = pos
            
            # Datos del diente
            datos_diente = self._obtener_datos_diente(diente)
            matriz_dientes[fila][col] = datos_diente if datos_diente else None
            
        
        return {
            "dientes": matriz_dientes,
            "movilidad": matriz_movilidad,
            "recesion": matriz_recesion,
        }

    # ============================================================================
    # MÉTODOS DE EXTRACCIÓN DE DATOS
    # ============================================================================
    
    def _obtener_datos_diente(self, diente: Diente) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos completos de un diente para Form033
        """
        # 1. Verificar ausencia
        if diente.ausente:
            simbolo_data = self.SIMBOLO_MAPPING['A'].copy()
            simbolo_data["codigo_fdi"] = diente.codigo_fdi
            simbolo_data["superficies_afectadas"] = []
            return simbolo_data
        
        # 2. Obtener todos los diagnósticos activos del diente
        diagnosticos_para_simbolo = []
        superficies_afectadas = set()
        
        
        keys_excluidas = ['movilidad_dental', 'recesion_gingival']

        for superficie in diente.superficies.all():
            for diag in superficie.diagnosticos.all():
                if diag.activo and diag.diagnostico_catalogo.key not in keys_excluidas:
                    diagnosticos_para_simbolo.append(diag)
                    superficies_afectadas.add(superficie.nombre)
        
        if not diagnosticos_para_simbolo:
            return None
        
        # 4. Seleccionar diagnóstico prioritario
        diag_prioritario = self._seleccionar_diagnostico_prioritario(diagnosticos_para_simbolo)
        
        # 5. Mapear a símbolo Form033
        simbolo_key = diag_prioritario.diagnostico_catalogo.simbolo_formulario_033
        
        # 6. Verificar si existe mapeo
        if not simbolo_key or simbolo_key not in self.SIMBOLO_MAPPING:
            logger.warning(
                f"[Form033] Símbolo Form033 no mapeado: '{simbolo_key}' "
                f"para diagnóstico {diag_prioritario.diagnostico_catalogo.key}"
            )
            return None
        
        simbolo_data = self.SIMBOLO_MAPPING[simbolo_key].copy()
        
        # 7. Agregar datos específicos
        simbolo_data.update({
            "codigo_fdi": diente.codigo_fdi,
            "superficies_afectadas": list(superficies_afectadas),
            "diagnostico_id": str(diag_prioritario.id),
            "fecha_diagnostico": diag_prioritario.fecha.isoformat(),
        })
        
        return simbolo_data
    
    def _seleccionar_diagnostico_prioritario(self, diagnosticos: List[DiagnosticoDental]) -> DiagnosticoDental:
        """
        Selecciona el diagnóstico más prioritario según:
        1. Prioridad del catálogo (5 = crítica, 1 = baja)
        2. Fecha más reciente
        """
        return max(
            diagnosticos,
            key=lambda d: (
                d.diagnostico_catalogo.prioridad,
                d.fecha
            )
        )
    
    def _obtener_movilidad(self, diente: Diente) -> Optional[Dict[str, Any]]:
        """
        Obtiene nivel de movilidad del diente
        Busca específicamente diagnósticos de tipo 'movilidad_dental'
        """
        # Buscar diagnóstico de movilidad dental específico
        for superficie in diente.superficies.all():
            for diag in superficie.diagnosticos.all():
                if not diag.activo:
                    continue
                
                # Si es un diagnóstico de movilidad_dental
                if diag.diagnostico_catalogo.key == "movilidad_dental":
                    # 1. Primero buscar en atributos_clinicos
                    movilidad_key = diag.atributos_clinicos.get('movilidad_dental')
                    if movilidad_key:
                        try:
                            opcion = OpcionAtributoClinico.objects.get(
                                tipo_atributo__key='movilidad_dental',
                                key=movilidad_key
                            )
                            return {
                                "grado": opcion.orden,  # 1, 2, 3, 4
                                "key": opcion.key,
                                "nombre": opcion.nombre,
                                "prioridad": opcion.prioridad or 1,
                                "diagnostico_id": str(diag.id),
                                "fecha_diagnostico": diag.fecha.isoformat(),
                            }
                        except OpcionAtributoClinico.DoesNotExist:
                            logger.warning(f"[Form033] Opción movilidad no encontrada: {movilidad_key}")
                    
                    # 2. Si no hay atributo, usar valor por defecto
                    return {
                        "grado": 1,
                        "key": "grado_1",
                        "nombre": "Movilidad Dental (diagnóstico general)",
                        "prioridad": 3,
                        "diagnostico_id": str(diag.id),
                        "fecha_diagnostico": diag.fecha.isoformat(),
                    }
        
        # También buscar en atributos clínicos de otros diagnósticos (compatibilidad)
        for superficie in diente.superficies.all():
            for diag in superficie.diagnosticos.all():
                if not diag.activo:
                    continue
                    
                movilidad_key = diag.atributos_clinicos.get('movilidad_dental')
                if movilidad_key:
                    try:
                        opcion = OpcionAtributoClinico.objects.get(
                            tipo_atributo__key='movilidad_dental',
                            key=movilidad_key
                        )
                        return {
                            "grado": opcion.orden,
                            "key": opcion.key,
                            "nombre": opcion.nombre,
                            "prioridad": opcion.prioridad or 1,
                            "diagnostico_id": str(diag.id),
                            "fecha_diagnostico": diag.fecha.isoformat(),
                        }
                    except OpcionAtributoClinico.DoesNotExist:
                        logger.warning(f"[Form033] Opción movilidad no encontrada: {movilidad_key}")
        
        # No hay movilidad registrada
        return None
    
    def _obtener_recesion(self, diente: Diente) -> Optional[Dict[str, Any]]:
        """
        Obtiene nivel de recesión gingival del diente
        Busca específicamente diagnósticos de tipo 'recesion_gingival'
        """
        # Buscar diagnóstico de recesión gingival específico
        for superficie in diente.superficies.all():
            for diag in superficie.diagnosticos.all():
                if not diag.activo:
                    continue
                
                # Si es un diagnóstico de recesion_gingival
                if diag.diagnostico_catalogo.key == "recesion_gingival":
                    # 1. Primero buscar en atributos_clinicos
                    recesion_key = diag.atributos_clinicos.get('gravedad_recesion')
                    if recesion_key:
                        try:
                            opcion = OpcionAtributoClinico.objects.get(
                                tipo_atributo__key='gravedad_recesion',
                                key=recesion_key
                            )
                            return {
                                "nivel": opcion.orden,  # 1=leve, 2=moderada, 3=severa
                                "key": opcion.key,
                                "nombre": opcion.nombre,
                                "prioridad": opcion.prioridad or 1,
                                "diagnostico_id": str(diag.id),
                                "fecha_diagnostico": diag.fecha.isoformat(),
                            }
                        except OpcionAtributoClinico.DoesNotExist:
                            logger.warning(f"[Form033] Opción recesión no encontrada: {recesion_key}")
                    
                    # 2. Si no hay atributo, usar valor por defecto
                    return {
                        "nivel": 1,
                        "key": "leve",
                        "nombre": "Recesión Gingival (diagnóstico general)",
                        "prioridad": 2,
                        "diagnostico_id": str(diag.id),
                        "fecha_diagnostico": diag.fecha.isoformat(),
                    }
        
        # También buscar en atributos clínicos de otros diagnósticos (compatibilidad)
        for superficie in diente.superficies.all():
            for diag in superficie.diagnosticos.all():
                if not diag.activo:
                    continue
                    
                recesion_key = diag.atributos_clinicos.get('gravedad_recesion')
                if recesion_key:
                    try:
                        opcion = OpcionAtributoClinico.objects.get(
                            tipo_atributo__key='gravedad_recesion',
                            key=recesion_key
                        )
                        return {
                            "nivel": opcion.orden,
                            "key": opcion.key,
                            "nombre": opcion.nombre,
                            "prioridad": opcion.prioridad or 1,
                            "diagnostico_id": str(diag.id),
                            "fecha_diagnostico": diag.fecha.isoformat(),
                        }
                    except OpcionAtributoClinico.DoesNotExist:
                        logger.warning(f"[Form033] Opción recesión no encontrada: {recesion_key}")
        
        # No hay recesión registrada
        return None

    # ============================================================================
    # MÉTODOS AUXILIARES
    # ============================================================================
    
    def _obtener_dientes_optimizado(self, paciente: Paciente) -> List[Diente]:
        """
        Obtiene dientes con prefetch optimizado
        """
        return list(
            Diente.objects.filter(paciente=paciente)
            .prefetch_related(
                Prefetch(
                    'superficies',
                    queryset=SuperficieDental.objects.prefetch_related(
                        Prefetch(
                            'diagnosticos',
                            queryset=DiagnosticoDental.objects.filter(activo=True)
                            .select_related('diagnostico_catalogo', 'diagnostico_catalogo__categoria')
                            .order_by('-diagnostico_catalogo__prioridad', '-fecha')
                        )
                    )
                )
            )
            .order_by('codigo_fdi')
        )
    
    @staticmethod
    def _es_permanente(codigo_fdi: str) -> bool:
        """Verifica si un código FDI es de diente permanente"""
        return codigo_fdi[0] in ['1', '2', '3', '4']
    
    @staticmethod
    def _calcular_edad(fecha_nacimiento: date) -> int:
        """Calcula edad actual"""
        today = date.today()
        return today.year - fecha_nacimiento.year - (
            (today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
        )
