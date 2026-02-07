# api/clinical_records/serializers/plan_tratamiento_serializers.py
"""
Serializers CORREGIDOS para Plan de Tratamiento
CAMPOS REALES del modelo PlanTratamiento:
- titulo (CharField)
- notas_generales (TextField)
- NO TIENE 'descripcion'
"""

from rest_framework import serializers
from api.odontogram.models import PlanTratamiento, SesionTratamiento


class SesionTratamientoDetalleCompletoSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para sesiones de tratamiento con informaciÃ³n completa
    """
    odontologo_info = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    total_diagnosticos = serializers.SerializerMethodField()
    total_procedimientos = serializers.SerializerMethodField()
    total_prescripciones = serializers.SerializerMethodField()
    
    class Meta:
        model = SesionTratamiento
        fields = [
            'id', 'numero_sesion', 'fecha_programada', 'fecha_realizacion',
            'estado', 'estado_display', 'odontologo_info',
            'diagnosticos_complicaciones', 'procedimientos', 'prescripciones',
            'notas', 'observaciones', 'total_diagnosticos', 'total_procedimientos',
            'total_prescripciones', 'fecha_creacion'
        ]
    
    def get_odontologo_info(self, obj):
        if obj.odontologo:
            return {
                "id": obj.odontologo.id,
                "nombres": obj.odontologo.nombres,
                "apellidos": obj.odontologo.apellidos,
            }
        return None
    
    def get_total_diagnosticos(self, obj):
        return len(obj.diagnosticos_complicaciones) if obj.diagnosticos_complicaciones else 0
    
    def get_total_procedimientos(self, obj):
        return len(obj.procedimientos) if obj.procedimientos else 0
    
    def get_total_prescripciones(self, obj):
        return len(obj.prescripciones) if obj.prescripciones else 0
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Formatear procedimientos
        if data.get('procedimientos'):
            for proc in data['procedimientos']:
                proc['descripcion_formateada'] = f"{proc.get('nombre', '')} - {proc.get('diente', '')}"
                if proc.get('codigo'):
                    proc['descripcion_formateada'] = f"[{proc['codigo']}] {proc['descripcion_formateada']}"
        
        # Formatear prescripciones
        if data.get('prescripciones'):
            for pres in data['prescripciones']:
                pres['descripcion_formateada'] = f"{pres.get('medicamento', '')} - {pres.get('dosis', '')}"
        
        return data


class PlanTratamientoCompletoSerializer(serializers.ModelSerializer):
    """
    Serializer completo del Plan de Tratamiento
    """
    sesiones = serializers.SerializerMethodField()
    paciente_info = serializers.SerializerMethodField()
    creado_por_info = serializers.SerializerMethodField()
    resumen_estadistico = serializers.SerializerMethodField()
    procedimientos_consolidados = serializers.SerializerMethodField()
    prescripciones_consolidadas = serializers.SerializerMethodField()
    diagnosticos_consolidados = serializers.SerializerMethodField()
    
    class Meta:
        model = PlanTratamiento
        fields = [
            'id', 'titulo', 'notas_generales',  # CORREGIDO: Sin 'descripcion'
            'fecha_creacion', 'fecha_edicion', 'activo',
            'paciente_info', 'creado_por_info',
            'sesiones', 'resumen_estadistico',
            'procedimientos_consolidados', 'prescripciones_consolidadas',
            'diagnosticos_consolidados'
        ]
    
    def get_paciente_info(self, obj):
        """InformaciÃ³n bÃ¡sica del paciente"""
        if obj.paciente:
            return {
                'id': str(obj.paciente.id),
                'nombres': obj.paciente.nombres,
                'apellidos': obj.paciente.apellidos,
                'cedula_pasaporte': obj.paciente.cedula_pasaporte,
            }
        return None
    
    def get_creado_por_info(self, obj):
        """InformaciÃ³n del usuario que creÃ³ el plan"""
        if obj.creado_por:
            return {
                'id': obj.creado_por.id,
                'nombres': obj.creado_por.nombres,
                'apellidos': obj.creado_por.apellidos,
            }
        return None
    
    def get_sesiones(self, obj):
        """Obtener todas las sesiones activas con datos completos"""
        sesiones = obj.sesiones.filter(activo=True).order_by('numero_sesion')
        return SesionTratamientoDetalleCompletoSerializer(sesiones, many=True).data
    
    def get_resumen_estadistico(self, obj):
        """Resumen estadÃ­stico del plan"""
        sesiones = obj.sesiones.filter(activo=True)
        
        total_diagnosticos = 0
        total_procedimientos = 0
        total_prescripciones = 0
        sesiones_completadas = 0
        sesiones_planificadas = 0
        sesiones_en_progreso = 0
        
        for sesion in sesiones:
            # Contar diagnÃ³sticos
            if sesion.diagnosticos_complicaciones:
                total_diagnosticos += len(sesion.diagnosticos_complicaciones)
            
            # Contar procedimientos
            if sesion.procedimientos:
                total_procedimientos += len(sesion.procedimientos)
            
            # Contar prescripciones
            if sesion.prescripciones:
                total_prescripciones += len(sesion.prescripciones)
            
            # Contar por estado
            if sesion.estado == SesionTratamiento.EstadoSesion.COMPLETADA:
                sesiones_completadas += 1
            elif sesion.estado == SesionTratamiento.EstadoSesion.PLANIFICADA:
                sesiones_planificadas += 1
            elif sesion.estado == SesionTratamiento.EstadoSesion.EN_PROGRESO:
                sesiones_en_progreso += 1
        
        return {
            'total_sesiones': sesiones.count(),
            'sesiones_completadas': sesiones_completadas,
            'sesiones_planificadas': sesiones_planificadas,
            'sesiones_en_progreso': sesiones_en_progreso,
            'total_diagnosticos': total_diagnosticos,
            'total_procedimientos': total_procedimientos,
            'total_prescripciones': total_prescripciones,
        }
    
    def get_procedimientos_consolidados(self, obj):
        """Consolidar todos los procedimientos de todas las sesiones"""
        procedimientos = []
        sesiones = obj.sesiones.filter(activo=True).order_by('numero_sesion')
        
        for sesion in sesiones:
            if sesion.procedimientos:
                for proc in sesion.procedimientos:
                    procedimiento_con_sesion = proc.copy()
                    procedimiento_con_sesion['sesion_numero'] = sesion.numero_sesion
                    procedimiento_con_sesion['sesion_fecha'] = sesion.fecha_programada.isoformat() if sesion.fecha_programada else None
                    procedimiento_con_sesion['sesion_estado'] = sesion.estado
                    procedimientos.append(procedimiento_con_sesion)
        
        return procedimientos
    
    def get_prescripciones_consolidadas(self, obj):
        """Consolidar todas las prescripciones de todas las sesiones"""
        prescripciones = []
        sesiones = obj.sesiones.filter(activo=True).order_by('numero_sesion')
        
        for sesion in sesiones:
            if sesion.prescripciones:
                for pres in sesion.prescripciones:
                    prescripcion_con_sesion = pres.copy()
                    prescripcion_con_sesion['sesion_numero'] = sesion.numero_sesion
                    prescripcion_con_sesion['sesion_fecha'] = sesion.fecha_programada.isoformat() if sesion.fecha_programada else None
                    prescripcion_con_sesion['sesion_estado'] = sesion.estado
                    prescripciones.append(prescripcion_con_sesion)
        
        return prescripciones
    
    def get_diagnosticos_consolidados(self, obj):
        """Consolidar todos los diagnÃ³sticos de todas las sesiones"""
        diagnosticos = []
        sesiones = obj.sesiones.filter(activo=True).order_by('numero_sesion')
        
        for sesion in sesiones:
            if sesion.diagnosticos_complicaciones:
                for diag in sesion.diagnosticos_complicaciones:
                    diagnostico_con_sesion = diag.copy()
                    diagnostico_con_sesion['sesion_numero'] = sesion.numero_sesion
                    diagnostico_con_sesion['sesion_fecha'] = sesion.fecha_programada.isoformat() if sesion.fecha_programada else None
                    diagnostico_con_sesion['sesion_estado'] = sesion.estado
                    diagnosticos.append(diagnostico_con_sesion)
        
        return diagnosticos


class PlanTratamientoResumenSerializer(serializers.ModelSerializer):
    """
    Serializer resumido del Plan de Tratamiento
    """
    total_sesiones = serializers.SerializerMethodField()
    sesiones_completadas = serializers.SerializerMethodField()
    
    class Meta:
        model = PlanTratamiento
        fields = [
            'id', 'titulo', 'notas_generales',  # CORREGIDO: Sin 'descripcion'
            'fecha_creacion', 'total_sesiones', 'sesiones_completadas', 'activo'
        ]
    
    def get_total_sesiones(self, obj):
        return obj.sesiones.filter(activo=True).count()
    
    def get_sesiones_completadas(self, obj):
        return obj.sesiones.filter(
            activo=True,
            estado=SesionTratamiento.EstadoSesion.COMPLETADA
        ).count()
        