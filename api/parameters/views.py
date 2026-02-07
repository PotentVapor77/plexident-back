# api/parameters/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db import models
from datetime import datetime, time

from api.users.permissions import UserBasedPermission
from .models import (
    ConfiguracionHorario, 
    DiagnosticoFrecuente, 
    MedicamentoFrecuente,
    ConfiguracionSeguridad,
    ConfiguracionNotificaciones,
    ParametroGeneral
)
from .serializers import (
    ConfiguracionHorarioSerializer, 
    DiagnosticoSerializer, 
    MedicamentoSerializer,
    ConfigSeguridadSerializer, 
    ConfigNotificacionesSerializer,
    ParametroGeneralSerializer, 
    ConfigHorarioBulkSerializer
)
from .services.horario_service import HorarioService
from .services.seguridad_service import SeguridadService
from .services.notificacion_service import NotificacionService

import logging
logger = logging.getLogger(__name__)


# ============================================================================
# PAGINACIÓN
# ============================================================================

class ParametroPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ============================================================================
# VIEWSETS
# ============================================================================

class ConfiguracionHorarioViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de horarios de atención (RF-07.1)"""
    queryset = ConfiguracionHorario.objects.all().order_by('dia_semana')
    serializer_class = ConfiguracionHorarioSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def semana_actual(self, request):
        """Obtener horarios de la semana actual"""
        horarios = self.get_queryset().filter(activo=True)
        serializer = self.get_serializer(horarios, many=True)
        return Response({
            'success': True,
            'horarios': serializer.data,
            'total': horarios.count()
        })
    
    @action(detail=False, methods=['get'])
    def verificar(self, request):
        """Verificar si es horario laboral en este momento"""
        es_laboral = HorarioService.es_horario_laboral()
        dia_actual = timezone.now().weekday()
        hora_actual = timezone.now().time()
        
        try:
            horario_hoy = ConfiguracionHorario.objects.get(dia_semana=dia_actual, activo=True)
            horario_str = f"{horario_hoy.apertura} - {horario_hoy.cierre}"
        except ConfiguracionHorario.DoesNotExist:
            horario_str = "No hay horario configurado para hoy"
        
        return Response({
            'success': True,
            'es_horario_laboral': es_laboral,
            'dia_actual': dia_actual,
            'hora_actual': hora_actual.strftime('%H:%M'),
            'horario_hoy': horario_str
        })
    
    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        """Actualizar múltiples horarios a la vez"""
        if request.user.rol != 'Administrador':
            return Response({
                'success': False,
                'error': 'Permiso denegado',
                'message': 'Solo administradores pueden modificar horarios'
            }, status=status.HTTP_403_FORBIDDEN)
        
        logger.info(f"🔵 bulk_update iniciado por {request.user.username}")
        logger.info(f"📦 Datos recibidos: {request.data}")
        
        # Validar estructura
        serializer = ConfigHorarioBulkSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"❌ Validación fallida: {serializer.errors}")
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Procesar horarios
        resultados = []
        errores = []
        
        for horario_data in serializer.validated_data.get('horarios', []):
            dia_semana = horario_data.get('dia_semana')
            
            try:
                # Convertir strings de tiempo
                apertura = horario_data.get('apertura')
                cierre = horario_data.get('cierre')
                
                if isinstance(apertura, str):
                    apertura = datetime.strptime(apertura[:5], '%H:%M').time()
                if isinstance(cierre, str):
                    cierre = datetime.strptime(cierre[:5], '%H:%M').time()
                
                # Validar horario
                valido, mensaje = HorarioService.validar_horario(apertura, cierre)
                
                if not valido:
                    errores.append({
                        'dia': dia_semana,
                        'error': mensaje
                    })
                    continue
                
                # Actualizar o crear
                horario, created = ConfiguracionHorario.objects.update_or_create(
                    dia_semana=dia_semana,
                    defaults={
                        'apertura': apertura,
                        'cierre': cierre,
                        'activo': horario_data.get('activo', True),
                        'actualizado_por': request.user
                    }
                )
                
                logger.info(f"✅ {'Creado' if created else 'Actualizado'}: {horario}")
                
                resultados.append({
                    'dia': dia_semana,
                    'id': str(horario.id),
                    'success': True,
                    'created': created
                })
                
            except Exception as e:
                logger.error(f"❌ Error procesando día {dia_semana}: {str(e)}", exc_info=True)
                errores.append({
                    'dia': dia_semana,
                    'error': str(e)
                })
        
        # Obtener horarios actualizados
        horarios = ConfiguracionHorario.objects.all().order_by('dia_semana')
        horarios_serializer = self.get_serializer(horarios, many=True)
        
        logger.info(f"🟢 bulk_update completado: {len(resultados)} exitosos, {len(errores)} errores")
        
        return Response({
            'success': True,
            'message': f'Horarios procesados: {len(resultados)} exitosos',
            'resultados': resultados,
            'errores': errores if errores else None,
            'horarios': horarios_serializer.data
        })


class DiagnosticoViewSet(viewsets.ModelViewSet):
    """ViewSet para catálogo de diagnósticos odontológicos (RF-07.2)"""
    queryset = DiagnosticoFrecuente.objects.filter(activo=True).order_by('categoria', 'nombre')
    serializer_class = DiagnosticoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ParametroPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        categoria = self.request.query_params.get('categoria')
        search = self.request.query_params.get('search', '').strip()
        
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        
        if search:
            queryset = queryset.filter(
                models.Q(nombre__icontains=search) |
                models.Q(codigo__icontains=search) |
                models.Q(descripcion__icontains=search)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def categorias(self, request):
        """Listar categorías de diagnósticos disponibles"""
        categorias = DiagnosticoFrecuente.objects.values_list('categoria', flat=True).distinct()
        return Response({
            'success': True,
            'categorias': list(categorias)
        })
    
    def perform_destroy(self, instance):
        """Soft delete: desactivar en lugar de eliminar"""
        instance.activo = False
        instance.save()
        logger.info(f"Diagnóstico {instance.codigo} desactivado por {self.request.user.username}")


class MedicamentoViewSet(viewsets.ModelViewSet):
    """ViewSet para catálogo de medicamentos frecuentes (RF-07.3)"""
    queryset = MedicamentoFrecuente.objects.filter(activo=True).order_by('nombre')
    serializer_class = MedicamentoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ParametroPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        categoria = self.request.query_params.get('categoria')
        via = self.request.query_params.get('via_administracion')
        search = self.request.query_params.get('search', '').strip()
        
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        
        if via:
            queryset = queryset.filter(via_administracion=via)
        
        if search:
            queryset = queryset.filter(
                models.Q(nombre__icontains=search) |
                models.Q(principio_activo__icontains=search) |
                models.Q(presentacion__icontains=search)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def categorias(self, request):
        """Listar categorías de medicamentos disponibles"""
        categorias = MedicamentoFrecuente.objects.values_list('categoria', flat=True).distinct()
        return Response({
            'success': True,
            'categorias': [cat for cat in categorias if cat]
        })
    
    @action(detail=False, methods=['get'])
    def vias_administracion(self, request):
        """Listar vías de administración disponibles"""
        vias = MedicamentoFrecuente.objects.values_list('via_administracion', flat=True).distinct()
        return Response({
            'success': True,
            'vias_administracion': list(vias)
        })
    
    def perform_destroy(self, instance):
        """Soft delete: desactivar en lugar de eliminar"""
        instance.activo = False
        instance.save()
        logger.info(f"Medicamento {instance.nombre} desactivado por {self.request.user.username}")


class ConfiguracionSeguridadViewSet(viewsets.ModelViewSet):
    """ViewSet para configuración de seguridad (RF-07.4, RF-07.5)"""
    queryset = ConfiguracionSeguridad.objects.all()
    serializer_class = ConfigSeguridadSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if not self.queryset.exists():
            config = ConfiguracionSeguridad.objects.create()
            return ConfiguracionSeguridad.objects.filter(pk=config.pk)
        return self.queryset
    
    def get_object(self):
        return self.get_queryset().first()
    
    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def validar_password(self, request):
        """Validar una contraseña según las reglas configuradas"""
        password = request.query_params.get('password', '')
        
        if not password:
            return Response({
                'success': False,
                'error': 'Se requiere el parámetro "password"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        config = self.get_object()
        resultado = SeguridadService.validar_complejidad_password(password, config)
        
        return Response({
            'success': True,
            'es_valida': resultado['es_valida'],
            'errores': resultado['errores'],
            'configuracion': {
                'longitud_minima': config.longitud_minima_password,
                'requiere_mayusculas': config.requiere_mayusculas,
                'requiere_numeros': config.requiere_numeros,
                'requiere_especiales': config.requiere_especiales
            }
        })
    
    def update(self, request, *args, **kwargs):
        if request.user.rol != 'Administrador':
            return Response({
                'success': False,
                'error': 'Permiso denegado',
                'message': 'Solo administradores pueden modificar la configuración de seguridad'
            }, status=status.HTTP_403_FORBIDDEN)
        
        response = super().update(request, *args, **kwargs)
        response.data['message'] = 'Configuración de seguridad actualizada'
        return response


class ConfiguracionNotificacionesViewSet(viewsets.ModelViewSet):
    """ViewSet para configuración de notificaciones (RF-07.7)"""
    queryset = ConfiguracionNotificaciones.objects.all()
    serializer_class = ConfigNotificacionesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if not self.queryset.exists():
            config = ConfiguracionNotificaciones.objects.create()
            return ConfiguracionNotificaciones.objects.filter(pk=config.pk)
        return self.queryset
    
    def get_object(self):
        return self.get_queryset().first()
    
    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'])
    def probar_recordatorio(self, request):
        """Probar envío de recordatorio (solo para testing)"""
        if request.user.rol != 'Administrador':
            return Response({
                'success': False,
                'error': 'Permiso denegado'
            }, status=status.HTTP_403_FORBIDDEN)
        
        email = request.data.get('email', request.user.correo)
        
        try:
            NotificacionService.enviar_email_prueba(
                email=email,
                config=self.get_object()
            )
            
            return Response({
                'success': True,
                'message': f'Email de prueba enviado a {email}'
            })
            
        except Exception as e:
            logger.error(f"Error enviando email de prueba: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        if request.user.rol != 'Administrador':
            return Response({
                'success': False,
                'error': 'Permiso denegado',
                'message': 'Solo administradores pueden modificar la configuración de notificaciones'
            }, status=status.HTTP_403_FORBIDDEN)
        
        response = super().update(request, *args, **kwargs)
        response.data['message'] = 'Configuración de notificaciones actualizada'
        return response


class ParametroGeneralViewSet(viewsets.ModelViewSet):
    """ViewSet para parámetros generales del sistema"""
    queryset = ParametroGeneral.objects.all().order_by('categoria', 'clave')
    serializer_class = ParametroGeneralSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        categoria = self.request.query_params.get('categoria')
        
        if categoria:
            queryset = queryset.filter(categoria=categoria)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def categorias(self, request):
        """Listar categorías de parámetros disponibles"""
        categorias = ParametroGeneral.objects.values_list('categoria', flat=True).distinct()
        return Response({
            'success': True,
            'categorias': list(categorias)
        })
    
    @action(detail=False, methods=['get'])
    def obtener_por_clave(self, request):
        """Obtener parámetro por clave"""
        clave = request.query_params.get('clave')
        
        if not clave:
            return Response({
                'success': False,
                'error': 'Se requiere el parámetro "clave"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            parametro = ParametroGeneral.objects.get(clave=clave)
            serializer = self.get_serializer(parametro)
            return Response({
                'success': True,
                'parametro': serializer.data
            })
        except ParametroGeneral.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Parámetro "{clave}" no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def update(self, request, *args, **kwargs):
        if request.user.rol != 'Administrador':
            return Response({
                'success': False,
                'error': 'Permiso denegado',
                'message': 'Solo administradores pueden modificar parámetros'
            }, status=status.HTTP_403_FORBIDDEN)
        
        return super().update(request, *args, **kwargs)