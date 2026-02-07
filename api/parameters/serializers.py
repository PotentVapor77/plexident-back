# api/parameters/serializers.py
from rest_framework import serializers
from .models import (
    ConfiguracionHorario, 
    DiagnosticoFrecuente, 
    MedicamentoFrecuente,
    ConfiguracionSeguridad,
    ConfiguracionNotificaciones,
    ParametroGeneral
)
import re
from datetime import time


# ============================================================================
# SERIALIZERS BÁSICOS
# ============================================================================

class ConfiguracionHorarioSerializer(serializers.ModelSerializer):
    """Serializer para un horario individual"""
    dia_semana_nombre = serializers.CharField(source='get_dia_semana_display', read_only=True)
    
    class Meta:
        model = ConfiguracionHorario
        fields = [
            'id', 'dia_semana', 'dia_semana_nombre', 'apertura', 'cierre', 'activo',
            'creado_por', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['id', 'creado_por', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion']
    
    def validate(self, data):
        """Validar horarios"""
        apertura = data.get('apertura')
        cierre = data.get('cierre')
        
        if apertura and cierre:
            if apertura >= cierre:
                raise serializers.ValidationError({
                    'cierre': 'La hora de cierre debe ser posterior a la hora de apertura'
                })
            
            if apertura < time(5, 0):
                raise serializers.ValidationError({
                    'apertura': 'La hora de apertura no puede ser antes de las 5:00 AM'
                })
            
            if cierre > time(23, 0):
                raise serializers.ValidationError({
                    'cierre': 'La hora de cierre no puede ser después de las 11:00 PM'
                })
        
        return data


class DiagnosticoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosticoFrecuente
        fields = [
            'id', 'codigo', 'nombre', 'descripcion', 'categoria', 'activo',
            'creado_por', 'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['id', 'creado_por', 'fecha_creacion', 'fecha_modificacion']
    
    def validate_codigo(self, value):
        if not re.match(r'^[A-Z]{3}-\d{3}$', value):
            raise serializers.ValidationError('Formato de código inválido. Use: AAA-999')
        
        if self.instance:
            if DiagnosticoFrecuente.objects.filter(codigo=value).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError('Este código ya está registrado')
        else:
            if DiagnosticoFrecuente.objects.filter(codigo=value).exists():
                raise serializers.ValidationError('Este código ya está registrado')
        
        return value


class MedicamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicamentoFrecuente
        fields = [
            'id', 'nombre', 'principio_activo', 'presentacion', 
            'dosis_habitual', 'via_administracion', 'categoria', 'activo',
            'creado_por', 'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['id', 'creado_por', 'fecha_creacion', 'fecha_modificacion']
    
    def validate_nombre(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError('El nombre debe tener al menos 3 caracteres')
        
        qs = MedicamentoFrecuente.objects.filter(nombre__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise serializers.ValidationError('Ya existe un medicamento con este nombre')
        
        return value.strip()


class ConfigSeguridadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionSeguridad
        fields = [
            'id', 'tiempo_inactividad_minutos', 'max_intentos_login', 
            'duracion_bloqueo_minutos', 'longitud_minima_password',
            'requiere_mayusculas', 'requiere_numeros', 'requiere_especiales',
            'historial_password_cantidad', 'dias_validez_password',
            'actualizado_por', 'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['id', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion']
    
    def validate(self, data):
        if data.get('tiempo_inactividad_minutos', 0) < 1:
            raise serializers.ValidationError({
                'tiempo_inactividad_minutos': 'Debe ser al menos 1 minuto'
            })
        
        if data.get('max_intentos_login', 0) < 1:
            raise serializers.ValidationError({
                'max_intentos_login': 'Debe ser al menos 1 intento'
            })
        
        if data.get('longitud_minima_password', 0) < 4:
            raise serializers.ValidationError({
                'longitud_minima_password': 'La longitud mínima debe ser al menos 4 caracteres'
            })
        
        if data.get('longitud_minima_password', 0) > 50:
            raise serializers.ValidationError({
                'longitud_minima_password': 'La longitud máxima no puede exceder 50 caracteres'
            })
        
        return data


class ConfigNotificacionesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionNotificaciones
        fields = [
            'id', 'recordatorio_citas_horas_antes', 'enviar_email', 'enviar_sms',
            'hora_envio_diaria', 'asunto_email_recordatorio', 'plantilla_sms',
            'actualizado_por', 'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['id', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion']
    
    def validate_recordatorio_citas_horas_antes(self, value):
        if value < 1:
            raise serializers.ValidationError('Debe ser al menos 1 hora')
        if value > 168:
            raise serializers.ValidationError('No puede exceder 7 días (168 horas)')
        return value


class ParametroGeneralSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParametroGeneral
        fields = ['id', 'clave', 'valor', 'descripcion', 'categoria', 'tipo', 
                 'fecha_creacion', 'fecha_modificacion']
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']


# ============================================================================
# SERIALIZERS PARA BULK OPERATIONS (SIN USAR ModelSerializer)
# ============================================================================

class ConfigHorarioBulkSerializer(serializers.Serializer):
    """Serializer para actualización masiva sin validación de unique_together"""
    horarios = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=7
    )
    
    def validate_horarios(self, value):
        """Validar estructura y duplicados manualmente"""
        if not value:
            raise serializers.ValidationError('Se requiere al menos un horario')
        
        dias_vistos = {}
        
        for i, horario in enumerate(value):
            # Validar campos requeridos
            if 'dia_semana' not in horario:
                raise serializers.ValidationError(f'Horario {i}: falta dia_semana')
            
            if 'apertura' not in horario or 'cierre' not in horario:
                raise serializers.ValidationError(f'Horario {i}: faltan apertura o cierre')
            
            dia = horario.get('dia_semana')
            
            # Validar duplicados EN EL REQUEST
            if dia in dias_vistos:
                raise serializers.ValidationError(
                    f"El día {dia} está duplicado (posiciones {dias_vistos[dia]} y {i})"
                )
            
            dias_vistos[dia] = i
            
            # Validar rango de día
            if not isinstance(dia, int) or not (0 <= dia <= 6):
                raise serializers.ValidationError(f'dia_semana {dia} debe ser un entero entre 0 y 6')
        
        return value
