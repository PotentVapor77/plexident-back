# api/dashboard/serializers.py

from rest_framework import serializers


class AccesoRapidoSerializer(serializers.Serializer):
    """Serializer para accesos rápidos del dashboard"""
    accion = serializers.CharField()
    label = serializers.CharField()
    icon = serializers.CharField()


class FiltroFechasSerializer(serializers.Serializer):
    """
    ✅ RF-06.6: Serializer para validar filtros de fecha
    """
    fecha_inicio = serializers.DateField(
        format='%Y-%m-%d',
        input_formats=['%Y-%m-%d'],
        required=False,
        help_text="Fecha inicio en formato YYYY-MM-DD"
    )
    fecha_fin = serializers.DateField(
        format='%Y-%m-%d',
        input_formats=['%Y-%m-%d'],
        required=False,
        help_text="Fecha fin en formato YYYY-MM-DD"
    )
    periodo = serializers.ChoiceField(
        choices=['dia', 'semana', 'mes', 'trimestre', 'anio', 'personalizado'],
        required=False,
        default='mes'
    )

    def validate(self, data):
        """Validar que fecha_inicio <= fecha_fin"""
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin:
            if fecha_inicio > fecha_fin:
                raise serializers.ValidationError(
                    "fecha_inicio no puede ser mayor que fecha_fin"
                )
        
        return data


class DistribucionEstadoSerializer(serializers.Serializer):
    """Serializer para distribución de citas por estado"""
    estado = serializers.CharField()
    estado_display = serializers.CharField()
    total = serializers.IntegerField()
    porcentaje = serializers.FloatField()


class PeriodoSerializer(serializers.Serializer):
    """Serializer para información de periodo"""
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()


class EstadisticasNumericasSerializer(serializers.Serializer):
    """Estadísticas numéricas de citas"""
    total = serializers.IntegerField()
    programadas = serializers.IntegerField()
    confirmadas = serializers.IntegerField()
    en_atencion = serializers.IntegerField()
    asistidas = serializers.IntegerField()
    no_asistidas = serializers.IntegerField()
    canceladas = serializers.IntegerField()


class EvolucionDiariaSerializer(serializers.Serializer):
    """Evolución de citas por día"""
    fecha = serializers.DateField()
    total = serializers.IntegerField()


class EstadisticasCitasSerializer(serializers.Serializer):
    """
    ✅ RF-06.2: Serializer para estadísticas completas de citas
    """
    periodo = PeriodoSerializer()
    estadisticas = EstadisticasNumericasSerializer()
    distribucion_estados = DistribucionEstadoSerializer(many=True)
    promedio_diario = serializers.FloatField()
    evolucion_diaria = EvolucionDiariaSerializer(many=True)
    metadata = serializers.DictField(required=False)


class DashboardStatsSerializer(serializers.Serializer):
    """
    Serializer principal para respuesta del dashboard de Plexident
    Soporta diferentes vistas según el rol
    """
    rol = serializers.CharField()
    metricas = serializers.DictField()
    graficos = serializers.DictField(required=False)
    tablas = serializers.DictField(required=False)
    listas = serializers.DictField(required=False)
    accesos_rapidos = AccesoRapidoSerializer(many=True, required=False)
    mensaje = serializers.CharField(required=False)
    timestamp = serializers.DateTimeField(required=False)
    usuario = serializers.DictField(required=False)


class KPIsSerializer(serializers.Serializer):
    """
    ✅ RF-06.1: Serializer para KPIs principales
    """
    total_pacientes_activos = serializers.IntegerField()
    citas_hoy = serializers.IntegerField()
    citas_semana = serializers.IntegerField()
    promedio_citas_diarias = serializers.FloatField()
    citas_asistidas_hoy = serializers.IntegerField(required=False)
    citas_en_atencion = serializers.IntegerField(required=False)
    signos_vitales_hoy = serializers.IntegerField(required=False)
    periodo = serializers.CharField()
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()
    fecha_actual = serializers.DateField()


class OverviewSerializer(serializers.Serializer):
    """Serializer para vista overview rápida"""
    total_pacientes = serializers.IntegerField()
    pacientes_activos = serializers.IntegerField()
    citas_hoy = serializers.IntegerField()
    signos_vitales_hoy = serializers.IntegerField()
    rol = serializers.CharField()
    fecha = serializers.DateField()
    timestamp = serializers.DateTimeField()