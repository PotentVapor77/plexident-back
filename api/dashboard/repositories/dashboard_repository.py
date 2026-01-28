# api/dashboard/repositories/dashboard_repository.py

import logging
from django.db.models import Count, Q, Sum, Avg, Case, When, Value, IntegerField, FloatField, OuterRef, Subquery
from django.db.models.functions import TruncMonth, TruncWeek, TruncDate, Coalesce, TruncDay, TruncHour
from django.utils import timezone
from datetime import timedelta, datetime, date
import pytz  # ✅ AGREGADO

from api.patients.models.paciente import Paciente
from api.patients.models.constantes_vitales import ConstantesVitales
from api.users.models import Usuario
from api.appointment.models import Cita, EstadoCita

logger = logging.getLogger(__name__)

# ✅✅✅ TIMEZONE DE ECUADOR ✅✅✅
ECUADOR_TZ = pytz.timezone('America/Guayaquil')


def get_fecha_local_ecuador() -> date:
    """
    ✅ Retorna la fecha actual en Ecuador (UTC-5)
    Siempre usar esta función en lugar de timezone.now().date()
    """
    return timezone.now().astimezone(ECUADOR_TZ).date()


class DashboardRepository:
    """
    Repositorio para consultas de datos del dashboard de Plexident
    Incluye soporte para filtros de fecha personalizables
    """

    # ==================== UTILIDADES DE FECHAS ====================

    @staticmethod
    def parsear_fecha(fecha_str):
        """Convierte string a date, maneja errores"""
        if not fecha_str:
            return None
        if isinstance(fecha_str, date):
            return fecha_str
        if isinstance(fecha_str, str):
            try:
                return datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.fromisoformat(fecha_str.replace('Z', '+00:00')).date()
                except:
                    logger.error(f"No se pudo parsear fecha: {fecha_str}")
                    return None
        return None

    @staticmethod
    def get_fechas_filtro(fecha_inicio=None, fecha_fin=None, periodo=None):
        """
        ✅ CORREGIDO: Retorna las fechas de filtro según parámetros usando hora LOCAL de Ecuador
        """
        # ✅✅✅ USAR FECHA LOCAL DE ECUADOR ✅✅✅
        hoy = get_fecha_local_ecuador()
        
        # Si hay fechas personalizadas, usarlas
        if fecha_inicio or fecha_fin:
            fecha_inicio_parsed = DashboardRepository.parsear_fecha(fecha_inicio)
            fecha_fin_parsed = DashboardRepository.parsear_fecha(fecha_fin)
            
            if fecha_inicio_parsed and fecha_fin_parsed:
                return {
                    'fecha_inicio': fecha_inicio_parsed,
                    'fecha_fin': fecha_fin_parsed,
                    'hoy': hoy,
                    'periodo': 'personalizado'
                }
        
        # Calcular según periodo
        periodo = periodo or 'mes'
        
        if periodo == 'hoy' or periodo == 'dia':
            fecha_inicio = hoy
            fecha_fin = hoy
        elif periodo == 'semana' or periodo == 'semana_actual':
            # Lunes a Domingo de esta semana
            fecha_inicio = hoy - timedelta(days=hoy.weekday())  # Lunes
            fecha_fin = fecha_inicio + timedelta(days=6)        # Domingo
        elif periodo == 'trimestre' or periodo == 'trimestre_actual':
            # Primer día del trimestre actual hasta HOY
            mes_actual = hoy.month
            trimestre = (mes_actual - 1) // 3
            mes_inicio_trimestre = trimestre * 3 + 1
            fecha_inicio = hoy.replace(month=mes_inicio_trimestre, day=1)
            fecha_fin = hoy  # Hasta hoy, no hasta fin de trimestre
        elif periodo == 'anio' or periodo == 'anio_actual':
            fecha_inicio = hoy.replace(month=1, day=1)
            fecha_fin = hoy.replace(month=12, day=31)
        else:  # 'mes' o 'mes_actual' por defecto
            fecha_inicio = hoy.replace(day=1)
            # Último día del mes
            if hoy.month == 12:
                fecha_fin = hoy.replace(year=hoy.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                fecha_fin = (hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1))
        
        # Fechas auxiliares
        inicio_mes = hoy.replace(day=1)
        
        return {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'hoy': hoy,
            'inicio_mes': inicio_mes,
            'hace_7_dias': hoy - timedelta(days=7),
            'hace_30_dias': hoy - timedelta(days=30),
            'hace_6_meses': hoy - timedelta(days=180),
            'periodo': periodo
        }

    # ==================== MÉTRICAS COMUNES ====================

    @staticmethod
    def get_total_pacientes():
        """Total de pacientes registrados"""
        return Paciente.objects.count()

    @staticmethod
    def get_pacientes_activos():
        """Total de pacientes activos"""
        return Paciente.objects.filter(activo=True).count()
    
    @staticmethod
    def get_pacientes_inactivos():
        """Total de pacientes inactivos"""
        return Paciente.objects.filter(activo=False).count()

    @staticmethod
    def get_signos_vitales_hoy(hoy):
        """Signos vitales registrados hoy"""
        return ConstantesVitales.objects.filter(
            fecha_creacion__date=hoy,
            activo=True
        ).count()

    # ==================== RF-06.1: KPIs MEJORADOS ====================

    @staticmethod
    def get_citas_hoy(hoy):
        """Citas del día (todas menos canceladas)"""
        return Cita.objects.filter(
            fecha=hoy
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).count()

    @staticmethod
    def get_citas_semana(fecha_inicio, fecha_fin):
        """✅ RF-06.1: Total de citas de la semana"""
        return Cita.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).count()

    @staticmethod
    def get_promedio_citas_diarias(fecha_inicio, fecha_fin):
        """✅ RF-06.1: Promedio de citas diarias en el periodo"""
        total_citas = Cita.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).count()
        
        # Calcular días transcurridos en el periodo
        dias = max((fecha_fin - fecha_inicio).days + 1, 1)
        
        # Calcular solo sobre días laborables (lunes a sábado)
        dias_laborables = 0
        current_date = fecha_inicio
        while current_date <= fecha_fin:
            if current_date.weekday() < 6:  # 0=Lunes, 5=Sábado
                dias_laborables += 1
            current_date += timedelta(days=1)
        
        dias_efectivos = dias_laborables if dias_laborables > 0 else dias
        
        return round(total_citas / dias_efectivos, 2) if dias_efectivos > 0 else 0.0

    @staticmethod
    def get_citas_por_dia_periodo(fecha_inicio, fecha_fin):
        """Citas agrupadas por día en el periodo"""
        return list(
            Cita.objects.filter(
                fecha__gte=fecha_inicio,
                fecha__lte=fecha_fin
            ).exclude(
                estado=EstadoCita.CANCELADA
            ).values('fecha')
            .annotate(total=Count('id'))
            .order_by('fecha')
        )

    # ==================== RF-06.2: DISTRIBUCIÓN POR ESTADO ====================

    @staticmethod
    def get_distribucion_citas_por_estado(fecha_inicio, fecha_fin):
        """✅ RF-06.2: Distribución de citas por estado en el periodo"""
        total_general = Cita.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).count()
        
        if total_general == 0:
            return []
        
        distribucion = Cita.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).values('estado').annotate(
            total=Count('id')
        ).order_by('-total')
        
        resultado = []
        for item in distribucion:
            estado_display = dict(EstadoCita.choices).get(item['estado'], item['estado'])
            porcentaje = (item['total'] / total_general * 100)
            resultado.append({
                'estado': item['estado'],
                'estado_display': estado_display,
                'total': item['total'],
                'porcentaje': round(porcentaje, 2)
            })
        
        # Ajustar para que sume exactamente 100%
        suma_porcentajes = sum(item['porcentaje'] for item in resultado)
        
        if abs(suma_porcentajes - 100) > 0.01 and resultado:
            max_item = max(resultado, key=lambda x: x['porcentaje'])
            diferencia = 100 - suma_porcentajes
            max_item['porcentaje'] = round(max_item['porcentaje'] + diferencia, 2)
        
        return resultado

    @staticmethod
    def get_estadisticas_detalladas_citas(fecha_inicio, fecha_fin):
        """Estadísticas detalladas de citas para el periodo"""
        return Cita.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).aggregate(
            total=Count('id'),
            programadas=Count(Case(When(estado=EstadoCita.PROGRAMADA, then=1))),
            confirmadas=Count(Case(When(estado=EstadoCita.CONFIRMADA, then=1))),
            en_atencion=Count(Case(When(estado=EstadoCita.EN_ATENCION, then=1))),
            asistidas=Count(Case(When(estado=EstadoCita.ASISTIDA, then=1))),
            no_asistidas=Count(Case(When(estado=EstadoCita.NO_ASISTIDA, then=1))),
            canceladas=Count(Case(When(estado=EstadoCita.CANCELADA, then=1)))
        )

    # ==================== MÉTRICAS ADMINISTRADOR ====================

    @staticmethod
    def get_citas_mes(inicio_mes):
        """Total de citas del mes (todas menos canceladas)"""
        return Cita.objects.filter(
            fecha__gte=inicio_mes
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).count()

    @staticmethod
    def get_citas_asistidas_mes(inicio_mes):
        """Citas ASISTIDAS del mes"""
        return Cita.objects.filter(
            fecha__gte=inicio_mes,
            estado=EstadoCita.ASISTIDA
        ).count()

    @staticmethod
    def get_citas_asistidas_hoy(hoy):
        """Citas ASISTIDAS del día"""
        return Cita.objects.filter(
            fecha=hoy,
            estado=EstadoCita.ASISTIDA
        ).count()

    @staticmethod
    def get_citas_en_atencion_hoy(hoy):
        """Citas EN_ATENCION del día"""
        return Cita.objects.filter(
            fecha=hoy,
            estado=EstadoCita.EN_ATENCION
        ).count()

    @staticmethod
    def get_odontologos_activos():
        """Odontólogos activos en el sistema"""
        return Usuario.objects.filter(
            rol='Odontologo',
            is_active=True
        ).count()

    @staticmethod
    def get_evolucion_citas_meses(meses=6):
        """✅ CORREGIDO: Evolución de citas por mes usando fecha local"""
        MESES_ES = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        
        MESES_CORTOS_ES = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr',
            5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago',
            9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
        }
        
        evolucion = []
        # ✅✅✅ USAR FECHA LOCAL ✅✅✅
        hoy = get_fecha_local_ecuador()
        
        for i in range(meses):
            mes_inicio = (hoy.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            mes_fin = (mes_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            total = Cita.objects.filter(
                fecha__gte=mes_inicio,
                fecha__lte=mes_fin,
                estado=EstadoCita.ASISTIDA
            ).count()
            
            mes_numero = mes_inicio.month
            año = mes_inicio.year
            
            mes_largo = f"{MESES_ES[mes_numero]} {año}"
            mes_corto = f"{MESES_CORTOS_ES[mes_numero]} {año}"
            
            evolucion.insert(0, {
                'mes': mes_largo,
                'mes_corto': mes_corto,
                'total': total,
                'mes_numero': mes_numero,
                'año': año,
                'fecha_inicio': mes_inicio.isoformat(),
                'fecha_fin': mes_fin.isoformat()
            })
        
        return evolucion

    @staticmethod
    def get_citas_por_odontologo_periodo(fecha_inicio, fecha_fin, limit=5):
        """Citas por odontólogo en el periodo - Solo ASISTIDAS"""
        return list(
            Cita.objects.filter(
                fecha__gte=fecha_inicio,
                fecha__lte=fecha_fin,
                estado=EstadoCita.ASISTIDA
            ).values('odontologo__username', 'odontologo__nombres', 'odontologo__apellidos')
            .annotate(total=Count('id'))
            .order_by('-total')[:limit]
        )

    @staticmethod
    def get_distribucion_genero():
        """Distribución de pacientes por género"""
        return list(
            Paciente.objects.filter(activo=True)
            .values('sexo')
            .annotate(total=Count('id'))
        )

    @staticmethod
    def get_motivos_consulta_frecuentes(fecha_inicio, fecha_fin, limit=5):
        """Motivos de consulta más frecuentes en el periodo"""
        return list(
            Cita.objects.filter(
                fecha__gte=fecha_inicio,
                fecha__lte=fecha_fin,
                estado=EstadoCita.ASISTIDA
            ).exclude(
                Q(motivo_consulta__isnull=True) | Q(motivo_consulta='')
            ).values('motivo_consulta')
            .annotate(total=Count('id'))
            .order_by('-total')[:limit]
        )

    @staticmethod
    def get_ultimas_citas(limit=5):
        """Últimas citas registradas (todas menos canceladas)"""
        return Cita.objects.filter(
            activo=True
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).select_related(
            'paciente', 'odontologo'
        ).order_by('-fecha', '-hora_inicio')[:limit]

    @staticmethod
    def get_pacientes_recientes(hace_7_dias, limit=5):
        """Pacientes registrados recientemente"""
        return Paciente.objects.filter(
            fecha_creacion__date__gte=hace_7_dias
        ).order_by('-fecha_creacion')[:limit]

    @staticmethod
    def get_usuarios_sistema():
        """Usuarios del sistema (con rol y estado)"""
        return Usuario.objects.filter(
            is_active=True
        ).values(
            'username', 'nombres', 'apellidos', 'rol', 'is_active'
        ).order_by('rol', 'nombres')

    # ==================== MÉTRICAS ODONTÓLOGO ====================

    @staticmethod
    def get_mis_pacientes_atendidos(user):
        """Mis pacientes atendidos (total ASISTIDAS)"""
        return Cita.objects.filter(
            odontologo=user,
            estado=EstadoCita.ASISTIDA
        ).values('paciente').distinct().count()

    @staticmethod
    def get_mis_citas_mes(user, inicio_mes):
        """Mis citas del mes (todas menos canceladas)"""
        return Cita.objects.filter(
            odontologo=user,
            fecha__gte=inicio_mes
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).count()

    @staticmethod
    def get_mis_citas_hoy(user, hoy):
        """Mis citas registradas hoy (todas menos canceladas)"""
        return Cita.objects.filter(
            odontologo=user,
            fecha=hoy
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).count()

    @staticmethod
    def get_mis_citas_asistidas_hoy(user, hoy):
        """Mis citas ASISTIDAS hoy"""
        return Cita.objects.filter(
            odontologo=user,
            fecha=hoy,
            estado=EstadoCita.ASISTIDA
        ).count()

    @staticmethod
    def get_pacientes_con_condiciones_importantes():
        """Pacientes con condiciones importantes según AnamnesisGeneral"""
        return Paciente.objects.filter(
            activo=True,
            anamnesis_general__isnull=False
        ).filter(
            Q(anamnesis_general__alergia_antibiotico__in=['PENICILINA', 'AMOXICILINA', 'CEFALEXINA', 'AZITROMICINA', 'CLARITROMICINA', 'OTRO']) |
            Q(anamnesis_general__alergia_anestesia__in=['LIDOCAINA', 'ARTICAINA', 'MEPIVACAINA', 'BUPIVACAINA', 'PRILOCAINA', 'OTRO']) |
            Q(anamnesis_general__hemorragias='SI') |
            Q(anamnesis_general__diabetes__in=['TIPO_1', 'TIPO_2', 'GESTACIONAL', 'PREDIABETES', 'LADA', 'OTRO']) |
            Q(anamnesis_general__hipertension_arterial__in=['CONTROLADA', 'LIMITROFE', 'NO_CONTROLADA', 'RESISTENTE', 'MALIGNA', 'OTRO']) |
            Q(anamnesis_general__enfermedad_cardiaca__in=['CARDIOPATIA_ISQUEMICA', 'INSUFICIENCIA_CARDIACA', 'ARRITMIA', 'VALVULOPATIA', 'CARDIOMIOPATIA', 'OTRO'])
        ).count()

    @staticmethod
    def get_mis_ultimas_citas(user, limit=10):
        """Mis últimas citas (todas menos canceladas)"""
        return Cita.objects.filter(
            odontologo=user
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).select_related('paciente').order_by('-fecha', '-hora_inicio')[:limit]

    @staticmethod
    def get_pacientes_con_condiciones_importantes_lista(limit=10):
        """Lista de pacientes con condiciones importantes"""
        pacientes = Paciente.objects.filter(
            activo=True,
            anamnesis_general__isnull=False
        ).filter(
            Q(anamnesis_general__alergia_antibiotico__in=['PENICILINA', 'AMOXICILINA', 'CEFALEXINA', 'AZITROMICINA', 'CLARITROMICINA', 'OTRO']) |
            Q(anamnesis_general__alergia_anestesia__in=['LIDOCAINA', 'ARTICAINA', 'MEPIVACAINA', 'BUPIVACAINA', 'PRILOCAINA', 'OTRO']) |
            Q(anamnesis_general__hemorragias='SI') |
            Q(anamnesis_general__diabetes__in=['TIPO_1', 'TIPO_2', 'GESTACIONAL', 'PREDIABETES', 'LADA', 'OTRO']) |
            Q(anamnesis_general__hipertension_arterial__in=['CONTROLADA', 'LIMITROFE', 'NO_CONTROLADA', 'RESISTENTE', 'MALIGNA', 'OTRO']) |
            Q(anamnesis_general__enfermedad_cardiaca__in=['CARDIOPATIA_ISQUEMICA', 'INSUFICIENCIA_CARDIACA', 'ARRITMIA', 'VALVULOPATIA', 'CARDIOMIOPATIA', 'OTRO'])
        ).select_related('anamnesis_general').order_by('-fecha_creacion')[:limit]
        
        return pacientes

    @staticmethod
    def get_pacientes_sin_consulta_reciente():
        """✅ CORREGIDO: Pacientes sin consulta reciente usando fecha local"""
        # ✅✅✅ USAR FECHA LOCAL ✅✅✅
        hace_6_meses = get_fecha_local_ecuador() - timedelta(days=180)
        
        pacientes_con_citas = Cita.objects.filter(
            fecha__gte=hace_6_meses,
            estado=EstadoCita.ASISTIDA
        ).values_list('paciente_id', flat=True).distinct()
        
        return Paciente.objects.filter(
            activo=True
        ).exclude(
            id__in=pacientes_con_citas
        ).order_by('-fecha_creacion')[:10]

    @staticmethod
    def get_mis_citas_por_motivo(user):
        """Distribución de mis citas por motivo"""
        return list(
            Cita.objects.filter(
                odontologo=user,
                estado=EstadoCita.ASISTIDA
            ).values('motivo_consulta')
            .annotate(total=Count('id'))
            .order_by('-total')[:5]
        )

    @staticmethod
    def get_pacientes_sin_anamnesis():
        """Pacientes sin anamnesis general registrada"""
        return Paciente.objects.filter(
            activo=True,
            anamnesis_general__isnull=True
        ).count()

    @staticmethod
    def get_pacientes_sin_anamnesis_lista(limit=10):
        """Lista de pacientes sin anamnesis general"""
        return Paciente.objects.filter(
            activo=True,
            anamnesis_general__isnull=True
        ).order_by('-fecha_creacion')[:limit]

    # ==================== MÉTRICAS ASISTENTE ====================

    @staticmethod
    def get_pacientes_atendidos_hoy(hoy):
        """Pacientes atendidos hoy (ASISTIDAS)"""
        return Cita.objects.filter(
            fecha=hoy,
            estado=EstadoCita.ASISTIDA
        ).values('paciente').distinct().count()

    @staticmethod
    def get_citas_registradas_hoy(hoy):
        """Total de citas registradas hoy (todas menos canceladas)"""
        return Cita.objects.filter(
            fecha=hoy
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).count()

    @staticmethod
    def get_citas_programadas_hoy(hoy):
        """Citas PROGRAMADAS para hoy"""
        return Cita.objects.filter(
            fecha=hoy,
            estado=EstadoCita.PROGRAMADA
        ).count()

    @staticmethod
    def get_citas_confirmadas_hoy(hoy):
        """Citas CONFIRMADAS para hoy"""
        return Cita.objects.filter(
            fecha=hoy,
            estado=EstadoCita.CONFIRMADA
        ).count()

    @staticmethod
    def get_pacientes_nuevos_mes(inicio_mes):
        """Pacientes nuevos del mes"""
        return Paciente.objects.filter(
            fecha_creacion__date__gte=inicio_mes
        ).count()

    @staticmethod
    def get_ultimas_citas_dia(hoy, limit=10):
        """Últimas citas del día (todas menos canceladas)"""
        return Cita.objects.filter(
            fecha=hoy
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).select_related('paciente', 'odontologo').order_by('-hora_inicio')[:limit]

    @staticmethod
    def get_ultimos_signos_vitales(limit=10):
        """Últimos signos vitales registrados"""
        return ConstantesVitales.objects.filter(
            activo=True
        ).select_related('paciente', 'creado_por').order_by('-fecha_creacion')[:limit]

    @staticmethod
    def get_pacientes_sin_signos_vitales_recientes(dias=7, limit=10):
        """✅ CORREGIDO: Pacientes sin signos vitales recientes usando fecha local"""
        # ✅✅✅ USAR FECHA LOCAL ✅✅✅
        fecha_limite = get_fecha_local_ecuador() - timedelta(days=dias)
        
        pacientes_con_signos = ConstantesVitales.objects.filter(
            fecha_creacion__date__gte=fecha_limite,
            activo=True
        ).values_list('paciente_id', flat=True).distinct()
        
        return Paciente.objects.filter(
            activo=True
        ).exclude(
            id__in=pacientes_con_signos
        ).order_by('-fecha_creacion')[:limit]

    # ==================== RF-06.3: DIAGNÓSTICOS FRECUENTES ====================
    @staticmethod
    def get_diagnosticos_frecuentes(fecha_inicio, fecha_fin, limit=10):
        """
        ✅ RF-06.3: Diagnósticos más frecuentes en un periodo - VERSIÓN MEJORADA
        Agrupa por diagnóstico + diente (no por superficie individual)
        """
        try:
            from api.odontogram.models import DiagnosticoDental
            from django.db.models import Count, Case, When
            
            logger.info(f"🔍 Buscando diagnósticos frecuentes del sistema ({fecha_inicio} - {fecha_fin})")
            
            # ✅✅✅ PASO 1: Agrupar por DIAGNÓSTICO + DIENTE ✅✅✅
            diagnosticos_por_diente = DiagnosticoDental.objects.filter(
                fecha__date__gte=fecha_inicio,
                fecha__date__lte=fecha_fin,
                activo=True,
                diagnostico_catalogo__isnull=False
            ).values(
                'diagnostico_catalogo__id',
                'diagnostico_catalogo__key',
                'diagnostico_catalogo__nombre',
                'diagnostico_catalogo__siglas',
                'diagnostico_catalogo__categoria__nombre',
                'superficie__diente__codigo_fdi'  # ✅ Agrupar también por diente
            ).annotate(
                total_superficies=Count('id'),  # Cuántas superficies del mismo diente
                activos=Count(Case(When(estado_tratamiento='ACTIVO', then=1))),
                tratados=Count(Case(When(estado_tratamiento='TRATADO', then=1)))
            ).order_by('diagnostico_catalogo__nombre', 'superficie__diente__codigo_fdi')
            
            logger.info(f"📊 Total combinaciones diagnóstico+diente en el sistema: {diagnosticos_por_diente.count()}")
            
            if not diagnosticos_por_diente.exists():
                logger.warning(f"⚠️ No hay diagnósticos en el periodo seleccionado")
                return []
            
            # ✅✅✅ PASO 2: Reagrupar por TIPO de diagnóstico ✅✅✅
            diagnosticos_agrupados = {}
            total_casos = 0  # Total de casos (diagnóstico+diente únicos)
            
            for item in diagnosticos_por_diente:
                diag_id = str(item['diagnostico_catalogo__id'])
                diente = item['superficie__diente__codigo_fdi']
                
                # Crear entrada si no existe
                if diag_id not in diagnosticos_agrupados:
                    diagnosticos_agrupados[diag_id] = {
                        'diagnostico_id': diag_id,
                        'diagnostico_key': item['diagnostico_catalogo__key'] or 'N/A',
                        'diagnostico_nombre': item['diagnostico_catalogo__nombre'] or 'Sin nombre',
                        'diagnostico_siglas': item['diagnostico_catalogo__siglas'] or 'N/A',
                        'categoria_nombre': item['diagnostico_catalogo__categoria__nombre'] or 'Sin categoría',
                        'total_casos': 0,  # Cantidad de dientes afectados
                        'total_superficies': 0,  # Total de superficies afectadas
                        'dientes_afectados': [],
                        'activos': 0,
                        'tratados': 0
                    }
                
                # ✅ Cada combinación diagnóstico+diente = 1 caso
                diagnosticos_agrupados[diag_id]['total_casos'] += 1
                diagnosticos_agrupados[diag_id]['total_superficies'] += item['total_superficies']
                diagnosticos_agrupados[diag_id]['activos'] += item.get('activos', 0)
                diagnosticos_agrupados[diag_id]['tratados'] += item.get('tratados', 0)
                
                # Agregar info del diente
                if diente:
                    diagnosticos_agrupados[diag_id]['dientes_afectados'].append({
                        'diente': diente,
                        'superficies': item['total_superficies']
                    })
                
                total_casos += 1  # ✅ Contar cada diente afectado como 1 caso
            
            # ✅✅✅ PASO 3: Construir resultado final ✅✅✅
            resultado = []
            
            for diag in sorted(diagnosticos_agrupados.values(), 
                            key=lambda x: x['total_casos'], 
                            reverse=True)[:limit]:
                
                # Porcentaje basado en CASOS (diagnóstico+diente)
                porcentaje = (diag['total_casos'] / total_casos * 100) if total_casos > 0 else 0
                
                # Ordenar dientes
                dientes_info = sorted(diag['dientes_afectados'], key=lambda x: x['diente'])
                dientes_lista = [d['diente'] for d in dientes_info]
                
                resultado.append({
                    'diagnostico_id': diag['diagnostico_id'],
                    'diagnostico_key': diag['diagnostico_key'],
                    'diagnostico_nombre': diag['diagnostico_nombre'],
                    'diagnostico_siglas': diag['diagnostico_siglas'],
                    'categoria_nombre': diag['categoria_nombre'],
                    'total': diag['total_casos'],  # ✅ Cantidad de dientes afectados
                    'total_superficies': diag['total_superficies'],  # ✅ Total de superficies
                    'dientes_afectados': len(dientes_lista),  # ✅ Cantidad de dientes únicos
                    'dientes_lista': dientes_lista,  # ✅ Lista de códigos FDI
                    'dientes_detalle': dientes_info,  # ✅ Info detallada por diente
                    'porcentaje': round(porcentaje, 2),
                    'activos': diag['activos'],
                    'tratados': diag['tratados']
                })
            
            logger.info(f"✅ Diagnósticos del sistema: {len(resultado)} tipos encontrados")
            
            # Debug: mostrar resumen
            if resultado:
                logger.info(f"📋 Top diagnósticos:")
                for i, diag in enumerate(resultado[:3], 1):
                    logger.info(f"   {i}. {diag['diagnostico_nombre']}: {diag['total']} diente(s), "
                            f"{diag['total_superficies']} superficie(s) - {diag['porcentaje']}%")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo diagnósticos frecuentes: {str(e)}", exc_info=True)
            return []




    @staticmethod
    def get_diagnosticos_frecuentes_por_diente(fecha_inicio, fecha_fin, limit=5):
        """Extensión RF-06.3: Diagnósticos más frecuentes por diente específico"""
        try:
            from api.odontogram.models import DiagnosticoDental
            
            diagnosticos_por_diente = DiagnosticoDental.objects.filter(
                fecha__date__gte=fecha_inicio,
                fecha__date__lte=fecha_fin,
                activo=True
            ).values(
                'superficie__diente__codigo_fdi',
                'diagnostico_catalogo__nombre',
                'diagnostico_catalogo__siglas'
            ).annotate(
                total=Count('id')
            ).order_by('superficie__diente__codigo_fdi', '-total')
            
            resultado = {}
            for item in diagnosticos_por_diente:
                codigo_fdi = item['superficie__diente__codigo_fdi']
                
                if codigo_fdi not in resultado:
                    resultado[codigo_fdi] = []
                
                if len(resultado[codigo_fdi]) < limit:
                    resultado[codigo_fdi].append({
                        'diagnostico': item['diagnostico_catalogo__nombre'],
                        'siglas': item['diagnostico_catalogo__siglas'],
                        'total': item['total']
                    })
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error obteniendo diagnósticos por diente: {str(e)}")
            return {}
        
    @staticmethod
    def get_signos_vitales_por_hora(fecha):
        """Signos vitales por hora del día"""
        return list(
            ConstantesVitales.objects.filter(
                fecha_creacion__date=fecha,
                activo=True
            ).annotate(
                hora=TruncHour('fecha_creacion')
            ).values('hora').annotate(
                total=Count('id')
            ).order_by('hora')
        )

    @staticmethod
    def get_distribucion_citas_por_estado_odontologo(odontologo, fecha_inicio, fecha_fin):
        """✅ Distribución de citas por estado para un odontólogo específico"""
        total_general = Cita.objects.filter(
            odontologo=odontologo,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).count()
        
        if total_general == 0:
            return []
        
        distribucion = Cita.objects.filter(
            odontologo=odontologo,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).values('estado').annotate(
            total=Count('id')
        ).order_by('-total')
        
        resultado = []
        for item in distribucion:
            estado_display = dict(EstadoCita.choices).get(item['estado'], item['estado'])
            porcentaje = (item['total'] / total_general * 100)
            resultado.append({
                'estado': item['estado'],
                'estado_display': estado_display,
                'total': item['total'],
                'porcentaje': round(porcentaje, 2)
            })
        
        # Ajustar para que sume exactamente 100%
        suma_porcentajes = sum(item['porcentaje'] for item in resultado)
        
        if abs(suma_porcentajes - 100) > 0.01 and resultado:
            max_item = max(resultado, key=lambda x: x['porcentaje'])
            diferencia = 100 - suma_porcentajes
            max_item['porcentaje'] = round(max_item['porcentaje'] + diferencia, 2)
        
        return resultado


    @staticmethod
    def get_diagnosticos_frecuentes_odontologo(odontologo, fecha_inicio, fecha_fin, limit=10):
        """
        ✅ VERSIÓN MEJORADA: Agrupa diagnósticos por tipo + diente
        Si un diente tiene Caries en 3 superficies → cuenta como 1 caso
        """
        try:
            from api.odontogram.models import DiagnosticoDental
            from django.db.models import Count, Case, When, Q
            
            logger.info(f"🔍 Buscando diagnósticos para {odontologo.username} ({fecha_inicio} - {fecha_fin})")
            
            # ✅ Determinar campo de filtro
            filter_kwargs = {
                'fecha__date__gte': fecha_inicio,
                'fecha__date__lte': fecha_fin,
                'activo': True,
                'diagnostico_catalogo__isnull': False  # ✅ Solo con catálogo
            }
            
            if hasattr(DiagnosticoDental, 'odontologo'):
                filter_kwargs['odontologo'] = odontologo
                logger.info(f"✅ Usando campo 'odontologo' para filtrar")
            elif hasattr(DiagnosticoDental, 'creado_por'):
                filter_kwargs['creado_por'] = odontologo
                logger.info(f"✅ Usando campo 'creado_por' para filtrar")
            else:
                logger.error(f"❌ No se encontró campo de relación con odontólogo")
                return []
            
            # ✅✅✅ PASO 1: Agrupar por DIAGNÓSTICO + DIENTE ✅✅✅
            diagnosticos_por_diente = DiagnosticoDental.objects.filter(
                **filter_kwargs
            ).values(
                'diagnostico_catalogo__id',
                'diagnostico_catalogo__key',
                'diagnostico_catalogo__nombre',
                'diagnostico_catalogo__siglas',
                'diagnostico_catalogo__categoria__nombre',
                'superficie__diente__codigo_fdi'  # ✅ Agrupar también por diente
            ).annotate(
                total_superficies=Count('id'),  # Cuántas superficies del mismo diente
                activos=Count(Case(When(estado_tratamiento='ACTIVO', then=1))),
                tratados=Count(Case(When(estado_tratamiento='TRATADO', then=1)))
            ).order_by('diagnostico_catalogo__nombre', 'superficie__diente__codigo_fdi')
            
            logger.info(f"📊 Total combinaciones diagnóstico+diente: {diagnosticos_por_diente.count()}")
            
            if not diagnosticos_por_diente.exists():
                logger.warning(f"⚠️ No hay diagnósticos para {odontologo.username}")
                return []
            
            # ✅✅✅ PASO 2: Reagrupar por TIPO de diagnóstico ✅✅✅
            diagnosticos_agrupados = {}
            total_casos = 0  # Total de casos (diagnóstico+diente únicos)
            
            for item in diagnosticos_por_diente:
                diag_id = str(item['diagnostico_catalogo__id'])
                diente = item['superficie__diente__codigo_fdi']
                
                # Crear entrada si no existe
                if diag_id not in diagnosticos_agrupados:
                    diagnosticos_agrupados[diag_id] = {
                        'diagnostico_id': diag_id,
                        'diagnostico_key': item['diagnostico_catalogo__key'] or 'N/A',
                        'diagnostico_nombre': item['diagnostico_catalogo__nombre'] or 'Sin nombre',
                        'diagnostico_siglas': item['diagnostico_catalogo__siglas'] or 'N/A',
                        'categoria_nombre': item['diagnostico_catalogo__categoria__nombre'] or 'Sin categoría',
                        'total_casos': 0,  # Cantidad de dientes afectados
                        'total_superficies': 0,  # Total de superficies afectadas
                        'dientes_afectados': [],
                        'activos': 0,
                        'tratados': 0
                    }
                
                # ✅ Cada combinación diagnóstico+diente = 1 caso
                diagnosticos_agrupados[diag_id]['total_casos'] += 1
                diagnosticos_agrupados[diag_id]['total_superficies'] += item['total_superficies']
                diagnosticos_agrupados[diag_id]['activos'] += item.get('activos', 0)
                diagnosticos_agrupados[diag_id]['tratados'] += item.get('tratados', 0)
                
                # Agregar info del diente
                if diente:
                    diagnosticos_agrupados[diag_id]['dientes_afectados'].append({
                        'diente': diente,
                        'superficies': item['total_superficies']
                    })
                
                total_casos += 1  # ✅ Contar cada diente afectado como 1 caso
            
            # ✅✅✅ PASO 3: Construir resultado final ✅✅✅
            resultado = []
            
            for diag in sorted(diagnosticos_agrupados.values(), 
                            key=lambda x: x['total_casos'], 
                            reverse=True)[:limit]:
                
                # Porcentaje basado en CASOS (diagnóstico+diente)
                porcentaje = (diag['total_casos'] / total_casos * 100) if total_casos > 0 else 0
                
                # Ordenar dientes
                dientes_info = sorted(diag['dientes_afectados'], key=lambda x: x['diente'])
                dientes_lista = [d['diente'] for d in dientes_info]
                
                resultado.append({
                    'diagnostico_id': diag['diagnostico_id'],
                    'diagnostico_key': diag['diagnostico_key'],
                    'diagnostico_nombre': diag['diagnostico_nombre'],
                    'diagnostico_siglas': diag['diagnostico_siglas'],
                    'categoria_nombre': diag['categoria_nombre'],
                    'total': diag['total_casos'],  # ✅ Cantidad de dientes afectados
                    'total_superficies': diag['total_superficies'],  # ✅ Total de superficies
                    'dientes_afectados': len(dientes_lista),  # ✅ Cantidad de dientes únicos
                    'dientes_lista': dientes_lista,  # ✅ Lista de códigos FDI
                    'dientes_detalle': dientes_info,  # ✅ Info detallada por diente
                    'porcentaje': round(porcentaje, 2),
                    'activos': diag['activos'],
                    'tratados': diag['tratados']
                })
            
            logger.info(f"✅ Diagnósticos para {odontologo.username}: {len(resultado)} tipos encontrados")
            
            # Debug: mostrar resumen
            if resultado:
                logger.info(f"📋 Top diagnósticos:")
                for i, diag in enumerate(resultado[:3], 1):
                    logger.info(f"   {i}. {diag['diagnostico_nombre']}: {diag['total']} diente(s), "
                            f"{diag['total_superficies']} superficie(s) - {diag['porcentaje']}%")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo diagnósticos frecuentes: {str(e)}", exc_info=True)
            return []



    @staticmethod
    def get_citas_por_dia_periodo_odontologo(odontologo, fecha_inicio, fecha_fin):
        """✅ Citas por día para un odontólogo específico"""
        return list(
            Cita.objects.filter(
                odontologo=odontologo,
                fecha__gte=fecha_inicio,
                fecha__lte=fecha_fin
            ).exclude(
                estado=EstadoCita.CANCELADA
            ).values('fecha')
            .annotate(total=Count('id'))
            .order_by('fecha')
        )

    @staticmethod
    def get_evolucion_citas_meses_odontologo(odontologo, meses=6):
        """✅ CORREGIDO: Evolución de citas por mes para un odontólogo usando fecha local"""
        MESES_ES = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        
        MESES_CORTOS_ES = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr',
            5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago',
            9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
        }
        
        evolucion = []
        # ✅✅✅ USAR FECHA LOCAL ✅✅✅
        hoy = get_fecha_local_ecuador()
        
        for i in range(meses):
            mes_inicio = (hoy.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            mes_fin = (mes_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            total = Cita.objects.filter(
                odontologo=odontologo,
                fecha__gte=mes_inicio,
                fecha__lte=mes_fin,
                estado=EstadoCita.ASISTIDA
            ).count()
            
            mes_numero = mes_inicio.month
            año = mes_inicio.year
            
            mes_largo = f"{MESES_ES[mes_numero]} {año}"
            mes_corto = f"{MESES_CORTOS_ES[mes_numero]} {año}"
            
            evolucion.insert(0, {
                'mes': mes_largo,
                'mes_corto': mes_corto,
                'total': total,
                'mes_numero': mes_numero,
                'año': año,
                'fecha_inicio': mes_inicio.isoformat(),
                'fecha_fin': mes_fin.isoformat()
            })
        
        return evolucion

    # ==================== MÉTRICAS ADICIONALES ODONTÓLOGO ====================

    @staticmethod
    def get_mis_citas_semana(odontologo, fecha_inicio, fecha_fin):
        """✅ Mis citas de la semana (todas menos canceladas)"""
        return Cita.objects.filter(
            odontologo=odontologo,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).count()

    @staticmethod
    def get_mis_promedio_citas_diarias(odontologo, fecha_inicio, fecha_fin):
        """✅ Promedio de mis citas diarias - SOLO días laborables (lunes a sábado)"""
        total_citas = Cita.objects.filter(
            odontologo=odontologo,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).count()
        
        # Calcular días laborables (lunes a sábado) en el periodo
        dias_laborables = 0
        current_date = fecha_inicio
        while current_date <= fecha_fin:
            if current_date.weekday() < 6:  # 0=Lunes, 5=Sábado
                dias_laborables += 1
            current_date += timedelta(days=1)
        
        return round(total_citas / dias_laborables, 2) if dias_laborables > 0 else 0.0

    @staticmethod
    def get_mis_citas_periodo(odontologo, fecha_inicio, fecha_fin):
        """✅ Mis citas en un periodo específico (todas menos canceladas)"""
        return Cita.objects.filter(
            odontologo=odontologo,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).exclude(
            estado=EstadoCita.CANCELADA
        ).count()
