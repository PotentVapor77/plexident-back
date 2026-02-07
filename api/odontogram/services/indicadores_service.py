# api/odontogram/indicadores/indicadores_service.py
"""
Servicio principal para Indicadores de Salud Bucal
"""

from typing import Dict, List, Optional
from django.db import transaction
from api.odontogram.models import IndicadoresSaludBucal
from api.odontogram.constants import NIVELES_FLUOROSIS, NIVELES_PERIODONTAL, TIPOS_OCLUSION
from api.odontogram.services.calculos_service import CalculosIndicadoresService
from api.odontogram.services.piezas_service import PiezasIndiceService
from django.utils import timezone

class IndicadoresSaludBucalService:
    """
    Servicio principal para manejar Indicadores de Salud Bucal
    """
    
    @staticmethod
    def crear_indicadores_completos(
        paciente_id: str,
        usuario_id: int,
        datos: Dict
    ) -> IndicadoresSaludBucal:
        """
        Crea un registro completo de indicadores de salud bucal
        Maneja piezas ausentes usando alternativas automáticamente
        """
        with transaction.atomic():
            # 1. Obtener información de piezas disponibles (incluye alternativas)
            info_piezas = PiezasIndiceService.obtener_informacion_piezas(paciente_id)
            
            # 2. Preparar datos para guardar
            datos_guardar = {
                'paciente_id': paciente_id,
                'creado_por_id': usuario_id,
            }
            
            # 3. Campos básicos
            campos_basicos = ['enfermedad_periodontal', 'tipo_oclusion', 
                            'nivel_fluorosis', 'nivel_gingivitis', 'observaciones']

            for campo in campos_basicos:
                if campo in datos:
                    datos_guardar[campo] = datos[campo]

            # 4. ✅ GUARDAR REFERENCIA de piezas_usadas_en_registro
            piezas_usadas_estructura = None
            if 'piezas_usadas_en_registro' in datos:
                # Si viene del serializer, usarlo directamente
                piezas_usadas_estructura = datos['piezas_usadas_en_registro']
                datos_guardar['piezas_usadas_en_registro'] = piezas_usadas_estructura
            else:
                # Si NO viene, crear estructura básica que se llenará después
                piezas_usadas_estructura = {
                    'piezas_mapeo': {},
                    'denticion': info_piezas.get('denticion'),
                    'estadisticas': info_piezas.get('estadisticas'),
                    'fecha_registro': str(timezone.now())
                }
                datos_guardar['piezas_usadas_en_registro'] = piezas_usadas_estructura

            # 5. Procesar CADA pieza índice
            piezas_indice = ['16', '11', '26', '36', '31', '46']

            for pieza_original in piezas_indice:
                mapeo_piezas = info_piezas.get('piezas_mapeo', {}) or info_piezas.get('piezas', {})
                
                if pieza_original not in mapeo_piezas:
                    for pieza_candidata, info in mapeo_piezas.items():
                        if info.get('codigo_usado') == pieza_original or info.get('codigo_original') == pieza_original:
                            pieza_info = info
                            break
                    else:
                        pieza_info = None
                else:
                    pieza_info = mapeo_piezas[pieza_original]
                
                if pieza_info:
                    pieza_usada = pieza_info.get('codigo_usado', pieza_original)
                    es_alternativa = pieza_info.get('es_alternativa', False)
                    disponible = pieza_info.get('disponible', True)
                    
                    if disponible:
                        for campo in ['placa', 'calculo', 'gingivitis']:
                            clave_original = f"pieza_{pieza_original}_{campo}"
                            clave_usada = f"pieza_{pieza_usada}_{campo}" if es_alternativa else None
                            
                            valor = None
                            if clave_original in datos:
                                valor = datos[clave_original]
                            elif clave_usada and clave_usada in datos:
                                valor = datos[clave_usada]
                            elif f"pieza_{pieza_usada}_{campo}" in datos:
                                valor = datos[f"pieza_{pieza_usada}_{campo}"]
                            
                            if valor is not None:
                                datos_guardar[clave_original] = valor
                        
                        # Solo llenar piezas_mapeo si NO vino del serializer
                        if 'piezas_usadas_en_registro' not in datos:
                            piezas_usadas_estructura['piezas_mapeo'][pieza_original] = {
                                'codigo_usado': pieza_usada,
                                'es_alternativa': es_alternativa,
                                'codigo_original': pieza_original,
                                'disponible': disponible,
                                'diente_id': pieza_info.get('diente_id'),
                                'ausente': pieza_info.get('ausente', False)
                            }
            
            # 6. Crear el registro
            indicadores = IndicadoresSaludBucal.objects.create(**datos_guardar)
            
            # 7. Calcular y guardar promedios
            IndicadoresSaludBucalService.calcular_y_guardar_promedios(indicadores)
            
            # 8. Calcular información detallada
            valores_placa = {}
            valores_calculo = {}
            valores_gingivitis = {}
            
            for pieza_original in piezas_indice:
                placa = getattr(indicadores, f"pieza_{pieza_original}_placa", None)
                calculo = getattr(indicadores, f"pieza_{pieza_original}_calculo", None)
                gingivitis = getattr(indicadores, f"pieza_{pieza_original}_gingivitis", None)
                
                if placa is not None:
                    valores_placa[pieza_original] = placa
                if calculo is not None:
                    valores_calculo[pieza_original] = calculo
                if gingivitis is not None:
                    valores_gingivitis[pieza_original] = gingivitis
            
            # 9. Preparar información de cálculo
            indicadores.informacion_calculo = {
                'denticion': info_piezas['denticion'],
                'estadisticas': info_piezas['estadisticas'],
                'calculos': CalculosIndicadoresService.calcular_resumen_completo(
                    valores_placa, valores_calculo, valores_gingivitis
                )
            }
            
            indicadores.piezas_usadas_en_registro = piezas_usadas_estructura
            
            indicadores.save(update_fields=[
                'informacion_calculo',
                'piezas_usadas_en_registro',
                'ohi_promedio_placa',
                'ohi_promedio_calculo',
                'gi_promedio_gingivitis'
            ])
            
            return indicadores
    
    @staticmethod
    def actualizar_indicadores(
        indicadores_id: str,
        usuario_id: int,
        datos: Dict
    ) -> IndicadoresSaludBucal:
        """
        Actualiza un registro existente de indicadores
        """
        with transaction.atomic():
            indicadores = IndicadoresSaludBucal.objects.get(id=indicadores_id)
            if indicadores.piezas_usadas_en_registro:
                piezas_originales = indicadores.piezas_usadas_en_registro
            else:
                # Si no hay registro, obtener información actual (para backward compatibility)
                info_piezas = PiezasIndiceService.obtener_informacion_piezas(str(indicadores.paciente_id))
                piezas_originales = {
                    pieza: info.get('codigo_usado') or pieza
                    for pieza, info in info_piezas.get('piezas_mapeo', {}) or info_piezas.get('piezas', {}).items()
                }
                # Guardar para futuras ediciones
                indicadores.piezas_usadas_en_registro = piezas_originales
            
            
            
            # Actualizar datos básicos
            campos_basicos = [
                'enfermedad_periodontal',
                'tipo_oclusion', 
                'nivel_fluorosis',
                'nivel_gingivitis',
                'observaciones'
            ]
            
            
            
            for campo in campos_basicos:
                if campo in datos:
                    setattr(indicadores, campo, datos[campo])
            
            # Actualizar valores por pieza
            info_piezas = PiezasIndiceService.obtener_informacion_piezas(str(indicadores.paciente_id))
            
            for pieza_original, pieza_usada in piezas_originales.items():
                # Placa
                placa_key = f"pieza_{pieza_original}_placa"
                if placa_key in datos:
                    setattr(indicadores, placa_key, datos[placa_key])
                
                # Cálculo
                calculo_key = f"pieza_{pieza_original}_calculo"
                if calculo_key in datos:
                    setattr(indicadores, calculo_key, datos[calculo_key])
                
                # Gingivitis
                gingivitis_key = f"pieza_{pieza_original}_gingivitis"
                if gingivitis_key in datos:
                    setattr(indicadores, gingivitis_key, datos[gingivitis_key])

            
            # Actualizar auditoría
            indicadores.actualizado_por_id = usuario_id
            
            # Calcular y guardar promedios (usando los valores actualizados)
            IndicadoresSaludBucalService.calcular_y_guardar_promedios(indicadores)
            
            # Recalcular información de cálculo con las PIEZAS ORIGINALES
            valores_placa = {}
            valores_calculo = {}
            valores_gingivitis = {}
            
            for pieza_original in piezas_originales.keys():
                placa = getattr(indicadores, f"pieza_{pieza_original}_placa", None)
                calculo = getattr(indicadores, f"pieza_{pieza_original}_calculo", None)
                gingivitis = getattr(indicadores, f"pieza_{pieza_original}_gingivitis", None)
                
                if placa is not None:
                    valores_placa[pieza_original] = placa
                
                if calculo is not None:
                    valores_calculo[pieza_original] = calculo
                
                if gingivitis is not None:
                    valores_gingivitis[pieza_original] = gingivitis
            
            # Actualizar información de cálculo
            indicadores.informacion_calculo = {
                'denticion': indicadores.informacion_calculo.get('denticion', 'permanente') if indicadores.informacion_calculo else 'permanente',
                'piezas_usadas_en_creacion': piezas_originales,
                'estadisticas': indicadores.informacion_calculo.get('estadisticas', {}) if indicadores.informacion_calculo else {},
                'calculos': CalculosIndicadoresService.calcular_resumen_completo(
                    valores_placa, valores_calculo, valores_gingivitis
                )
            }
            
            indicadores.save()
            
            return indicadores
    
    @staticmethod
    def calcular_y_guardar_promedios(indicadores: IndicadoresSaludBucal) -> IndicadoresSaludBucal:
        """
        Calcula y guarda los promedios de placa, cálculo y gingivitis
        """
        # Obtener información de piezas
        info_piezas = PiezasIndiceService.obtener_informacion_piezas(str(indicadores.paciente_id))
        
        # CORRECCIÓN: Usar 'piezas_mapeo' en lugar de 'piezas'
        piezas_data = info_piezas.get('piezas_mapeo', {}) or info_piezas.get('piezas', {})
        
        # Recopilar valores
        valores_placa = []
        valores_calculo = []
        valores_gingivitis = []
        
        for pieza_original in piezas_data.keys():  # ← CORREGIDO
            placa = getattr(indicadores, f"pieza_{pieza_original}_placa", None)
            calculo = getattr(indicadores, f"pieza_{pieza_original}_calculo", None)
            gingivitis = getattr(indicadores, f"pieza_{pieza_original}_gingivitis", None)
            
            if placa is not None:
                valores_placa.append(placa)
            
            if calculo is not None:
                valores_calculo.append(calculo)
            
            if gingivitis is not None:
                valores_gingivitis.append(gingivitis)
        
        # Calcular promedios
        indicadores.ohi_promedio_placa = sum(valores_placa) / len(valores_placa) if valores_placa else None
        indicadores.ohi_promedio_calculo = sum(valores_calculo) / len(valores_calculo) if valores_calculo else None
        indicadores.gi_promedio_gingivitis = sum(valores_gingivitis) / len(valores_gingivitis) if valores_gingivitis else None
        
        indicadores.save()
        return indicadores
    
    @staticmethod
    def obtener_resumen_indicadores(indicadores: IndicadoresSaludBucal) -> Dict:
        """
        Obtiene un resumen estructurado de los indicadores
        """
        info_piezas = PiezasIndiceService.obtener_informacion_piezas(str(indicadores.paciente_id))
        
        # Recopilar datos por pieza
        datos_piezas = []
        for pieza_original, info in info_piezas.get('piezas_mapeo', {}) or info_piezas.get('piezas', {}).items():
            datos_pieza = {
                'pieza_original': pieza_original,
                'pieza_usada': info.get('codigo_usado'),
                'es_alternativa': info.get('es_alternativa'),
                'disponible': info.get('disponible'),
                'placa': getattr(indicadores, f"pieza_{pieza_original}_placa", None),
                'calculo': getattr(indicadores, f"pieza_{pieza_original}_calculo", None),
                'gingivitis': getattr(indicadores, f"pieza_{pieza_original}_gingivitis", None)
            }
            datos_piezas.append(datos_pieza)
        
        # Calcular resumen completo
        valores_placa = {p['pieza_original']: p['placa'] for p in datos_piezas if p['placa'] is not None}
        valores_calculo = {p['pieza_original']: p['calculo'] for p in datos_piezas if p['calculo'] is not None}
        valores_gingivitis = {p['pieza_original']: p['gingivitis'] for p in datos_piezas if p['gingivitis'] is not None}
        
        calculos = CalculosIndicadoresService.calcular_resumen_completo(
            valores_placa, valores_calculo, valores_gingivitis
        )
        
        return {
            'id': str(indicadores.id),
            'paciente_id': str(indicadores.paciente_id),
            'paciente_nombre': f"{indicadores.paciente.nombres} {indicadores.paciente.apellidos}",
            'fecha': indicadores.fecha,
            'denticion': info_piezas['denticion'],
            'estadisticas_piezas': info_piezas['estadisticas'],
            'datos_piezas': datos_piezas,
            'calculos': calculos,
            'diagnosticos': {
                'enfermedad_periodontal': {
                    'valor': indicadores.enfermedad_periodontal,
                    'descripcion': NIVELES_PERIODONTAL.get(indicadores.enfermedad_periodontal, 'Sin datos')
                },
                'tipo_oclusion': {
                    'valor': indicadores.tipo_oclusion,
                    'descripcion': TIPOS_OCLUSION.get(indicadores.tipo_oclusion, 'Sin datos')
                },
                'nivel_fluorosis': {
                    'valor': indicadores.nivel_fluorosis,
                    'descripcion': NIVELES_FLUOROSIS.get(indicadores.nivel_fluorosis, 'Sin datos')
                },
                'nivel_gingivitis': {
                    'valor': indicadores.nivel_gingivitis,
                    'descripcion': indicadores.get_nivel_gingivitis_display() if indicadores.nivel_gingivitis else 'Sin datos'
                }
            },
            'observaciones': indicadores.observaciones,
            'promedios': {
                'placa': indicadores.ohi_promedio_placa,
                'calculo': indicadores.ohi_promedio_calculo,
                'gingivitis': indicadores.gi_promedio_gingivitis
            },
            'auditoria': {
                'creado_por': indicadores.creado_por.get_full_name() if indicadores.creado_por else None,
                'actualizado_por': indicadores.actualizado_por.get_full_name() if indicadores.actualizado_por else None,
                'fecha_creacion': indicadores.fecha,
                'fecha_modificacion': indicadores.fecha_modificacion
            }
        }
    @staticmethod
    def crear_indicadores_con_alternativas(paciente_id, usuario_id, datos_piezas):
        """
        Crea indicadores manejando automáticamente las alternativas
        """
        from ..services.piezas_service import PiezasIndiceService
        
        # 1. Obtener piezas disponibles
        info_piezas = PiezasIndiceService.obtener_informacion_piezas(paciente_id)
        
        # 2. Preparar datos para guardar en el modelo
        datos_guardar = {
            'paciente_id': paciente_id,
            'creado_por_id': usuario_id,
            'piezas_usadas_en_registro': {
                'piezas_mapeo': {},
                'denticion': info_piezas.get('denticion'),
                'estadisticas': info_piezas.get('estadisticas')
            }
        }
        
        # 3. Procesar cada pieza con su alternativa
        for pieza_original, info in info_piezas.get('piezas', {}).items():
            pieza_usada = info.get('codigo_usado', pieza_original)
            
            # Buscar datos para esta pieza (original o alternativa)
            datos_encontrados = {}
            for campo in ['placa', 'calculo', 'gingivitis']:
                # Intentar con la pieza original primero
                clave = f"{pieza_original}_{campo}"
                if clave in datos_piezas:
                    datos_encontrados[campo] = datos_piezas[clave]
                    datos_guardar[f"pieza_{pieza_original}_{campo}"] = datos_piezas[clave]
            
            if datos_encontrados:
                datos_guardar['piezas_usadas_en_registro']['piezas_mapeo'][pieza_original] = {
                    'codigo_usado': pieza_usada,
                    'es_alternativa': pieza_usada != pieza_original,
                    'codigo_original': pieza_original,
                    'datos': datos_encontrados
                }
        
        # 4. Crear el registro
        indicador = IndicadoresSaludBucal.objects.create(**datos_guardar)
        
        # 5. Calcular promedios
        IndicadoresSaludBucalService.calcular_y_guardar_promedios(indicador)
        
        return indicador