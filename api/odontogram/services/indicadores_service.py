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
        """
        with transaction.atomic():
            info_piezas = PiezasIndiceService.obtener_informacion_piezas(paciente_id)
            
            datos_basicos = {
                'enfermedad_periodontal': datos.get('enfermedad_periodontal'),
                'tipo_oclusion': datos.get('tipo_oclusion'),
                'nivel_fluorosis': datos.get('nivel_fluorosis'),
                'nivel_gingivitis': datos.get('nivel_gingivitis'),
                'observaciones': datos.get('observaciones'),
                'piezas_usadas_en_registro': piezas_usadas
            }
            
            valores_placa = {}
            valores_calculo = {}
            valores_gingivitis = {}
            piezas_usadas = {}
            for pieza_original, info in info_piezas['piezas'].items():
                pieza_usada = info.get('codigo_usado') or pieza_original
                
                # Placa - buscar usando la pieza que se está usando realmente
                placa_key = f"pieza_{pieza_usada}_placa"
                valor_placa = datos.get(placa_key)
                if pieza_usada:
                    piezas_usadas[pieza_original] = pieza_usada
                else:
                    piezas_usadas[pieza_original] = pieza_original
                # Solo asignar el valor si existe (no es None)
                if valor_placa is not None:
                    valores_placa[pieza_original] = valor_placa
                
                # Cálculo - buscar usando la pieza que se está usando realmente
                calculo_key = f"pieza_{pieza_usada}_calculo"
                valor_calculo = datos.get(calculo_key)
                
                if valor_calculo is not None:
                    valores_calculo[pieza_original] = valor_calculo
                
                # Gingivitis - buscar usando la pieza que se está usando realmente
                gingivitis_key = f"pieza_{pieza_usada}_gingivitis"
                valor_gingivitis = datos.get(gingivitis_key)
                
                if valor_gingivitis is not None:
                    if valor_gingivitis in [0, 1]:
                        valores_gingivitis[pieza_original] = valor_gingivitis
                    else:
                        # Opcional: convertir cualquier valor > 0 a 1, o simplemente ignorar
                        valores_gingivitis[pieza_original] = 1 if valor_gingivitis > 0 else 0
            
            # Crear el registro base
            indicadores = IndicadoresSaludBucal.objects.create(
                paciente_id=paciente_id,
                creado_por_id=usuario_id,
                **datos_basicos,
                **{f"pieza_{k}_placa": v for k, v in valores_placa.items()},
                **{f"pieza_{k}_calculo": v for k, v in valores_calculo.items()},
                **{f"pieza_{k}_gingivitis": v for k, v in valores_gingivitis.items()}
            )
            
            # Calcular y guardar promedios
            IndicadoresSaludBucalService.calcular_y_guardar_promedios(indicadores)
            
            # Agregar información de cálculo al registro
            indicadores.informacion_calculo = {
                'denticion': info_piezas['denticion'],
                'piezas_usadas': {
                    pieza: info['codigo_usado'] or pieza
                    for pieza, info in info_piezas['piezas'].items()
                },
                'estadisticas': info_piezas['estadisticas'],
                'calculos': CalculosIndicadoresService.calcular_resumen_completo(
                    valores_placa, valores_calculo, valores_gingivitis
                )
            }
            
            indicadores.save()
            
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
                    for pieza, info in info_piezas['piezas'].items()
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
        
        # Recopilar valores
        valores_placa = []
        valores_calculo = []
        valores_gingivitis = []
        
        for pieza_original in info_piezas['piezas'].keys():
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
        for pieza_original, info in info_piezas['piezas'].items():
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