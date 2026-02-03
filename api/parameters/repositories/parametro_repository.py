# api/parameters/repositories/parametro_repository.py
from django.db import transaction
from ..models import (
    DiagnosticoFrecuente, 
    MedicamentoFrecuente,
    ConfiguracionSeguridad,
    ConfiguracionNotificaciones,
    ParametroGeneral
)
import logging

logger = logging.getLogger(__name__)


class ParametroRepository:
    """Repositorio para operaciones con parámetros generales"""
    
    # ==================== DIAGNÓSTICOS ====================
    @staticmethod
    def get_diagnosticos_activos(categoria=None, search=None):
        """
        Obtener diagnósticos activos
        
        Args:
            categoria: Filtrar por categoría
            search: Buscar en nombre, código o descripción
        
        Returns:
            QuerySet de DiagnosticoFrecuente
        """
        queryset = DiagnosticoFrecuente.objects.filter(activo=True)
        
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(codigo__icontains=search) |
                Q(descripcion__icontains=search)
            )
        
        return queryset.order_by('categoria', 'nombre')
    
    @staticmethod
    def buscar_diagnostico_por_codigo(codigo: str):
        """Buscar diagnóstico por código"""
        try:
            return DiagnosticoFrecuente.objects.get(codigo=codigo, activo=True)
        except DiagnosticoFrecuente.DoesNotExist:
            return None
    
    @staticmethod
    @transaction.atomic
    def crear_diagnostico(data, usuario):
        """Crear nuevo diagnóstico"""
        try:
            diagnostico = DiagnosticoFrecuente.objects.create(
                codigo=data.get('codigo'),
                nombre=data.get('nombre'),
                descripcion=data.get('descripcion', ''),
                categoria=data.get('categoria'),
                creado_por=usuario,
                activo=True
            )
            
            logger.info(f"Diagnóstico creado: {diagnostico.codigo} - {diagnostico.nombre}")
            return diagnostico
            
        except Exception as e:
            logger.error(f"Error creando diagnóstico: {str(e)}")
            raise
    
    # ==================== MEDICAMENTOS ====================
    @staticmethod
    def get_medicamentos_activos(categoria=None, via=None, search=None):
        """
        Obtener medicamentos activos
        
        Args:
            categoria: Filtrar por categoría
            via: Filtrar por vía de administración
            search: Buscar en nombre, principio activo o presentación
        """
        queryset = MedicamentoFrecuente.objects.filter(activo=True)
        
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        
        if via:
            queryset = queryset.filter(via_administracion=via)
        
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(principio_activo__icontains=search) |
                Q(presentacion__icontains=search)
            )
        
        return queryset.order_by('nombre')
    
    @staticmethod
    def buscar_medicamento_por_nombre(nombre: str):
        """Buscar medicamento por nombre (case-insensitive)"""
        try:
            return MedicamentoFrecuente.objects.get(nombre__iexact=nombre, activo=True)
        except MedicamentoFrecuente.DoesNotExist:
            return None
    
    # ==================== CONFIGURACIONES ====================
    @staticmethod
    def get_configuracion_seguridad():
        """Obtener configuración de seguridad (crea una si no existe)"""
        try:
            config = ConfiguracionSeguridad.objects.first()
            if not config:
                config = ConfiguracionSeguridad.objects.create()
                logger.info("Configuración de seguridad creada por defecto")
            return config
        except Exception as e:
            logger.error(f"Error obteniendo configuración de seguridad: {str(e)}")
            raise
    
    @staticmethod
    def get_configuracion_notificaciones():
        """Obtener configuración de notificaciones (crea una si no existe)"""
        try:
            config = ConfiguracionNotificaciones.objects.first()
            if not config:
                config = ConfiguracionNotificaciones.objects.create()
                logger.info("Configuración de notificaciones creada por defecto")
            return config
        except Exception as e:
            logger.error(f"Error obteniendo configuración de notificaciones: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def actualizar_configuracion_seguridad(data, usuario):
        """Actualizar configuración de seguridad"""
        try:
            config = ParametroRepository.get_configuracion_seguridad()
            
            for field, value in data.items():
                if hasattr(config, field):
                    setattr(config, field, value)
            
            config.actualizado_por = usuario
            config.save()
            
            logger.info(f"Configuración de seguridad actualizada por {usuario.username}")
            return config
            
        except Exception as e:
            logger.error(f"Error actualizando configuración de seguridad: {str(e)}")
            raise
    
    # ==================== PARÁMETROS GENERALES ====================
    @staticmethod
    def get_parametro_por_clave(clave: str):
        """Obtener parámetro por clave"""
        try:
            return ParametroGeneral.objects.get(clave=clave)
        except ParametroGeneral.DoesNotExist:
            return None
    
    @staticmethod
    def get_parametros_por_categoria(categoria: str):
        """Obtener todos los parámetros de una categoría"""
        return ParametroGeneral.objects.filter(categoria=categoria).order_by('clave')
    
    @staticmethod
    @transaction.atomic
    def crear_o_actualizar_parametro(clave: str, valor, descripcion='', categoria='general', tipo='STRING'):
        """Crear o actualizar parámetro"""
        try:
            parametro, created = ParametroGeneral.objects.update_or_create(
                clave=clave,
                defaults={
                    'valor': str(valor),
                    'descripcion': descripcion,
                    'categoria': categoria,
                    'tipo': tipo
                }
            )
            
            action = "creado" if created else "actualizado"
            logger.info(f"Parámetro {action}: {clave} = {valor}")
            return parametro, created
            
        except Exception as e:
            logger.error(f"Error guardando parámetro {clave}: {str(e)}")
            raise
    
    @staticmethod
    def get_valor_parametro(clave: str, default=None):
        """
        Obtener valor de parámetro con conversión de tipo
        
        Args:
            clave: Clave del parámetro
            default: Valor por defecto si no existe
        
        Returns:
            Valor convertido al tipo correspondiente
        """
        parametro = ParametroRepository.get_parametro_por_clave(clave)
        
        if not parametro:
            return default
        
        try:
            if parametro.tipo == 'INTEGER':
                return int(parametro.valor)
            elif parametro.tipo == 'FLOAT':
                return float(parametro.valor)
            elif parametro.tipo == 'BOOLEAN':
                return parametro.valor.lower() in ('true', '1', 'yes', 'si')
            elif parametro.tipo == 'JSON':
                import json
                return json.loads(parametro.valor)
            else:  # STRING
                return parametro.valor
        except (ValueError, json.JSONDecodeError):
            logger.warning(f"Error convirtiendo parámetro {clave} tipo {parametro.tipo}")
            return default