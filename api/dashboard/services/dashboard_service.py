# api/dashboard/services/dashboard_service.py

from api.dashboard.repositories.dashboard_repository import DashboardRepository, get_fecha_local_ecuador
from api.appointment.models import EstadoCita
from datetime import timedelta
import logging
from django.utils import timezone
from api.users.models import Usuario
import pytz

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Servicio para lógica de negocio del dashboard de Plexident
    """

    @staticmethod
    def get_dashboard_data(user, fecha_inicio=None, fecha_fin=None, periodo='mes'):
        """
        Obtiene los datos del dashboard según el rol del usuario - VERSIÓN CORREGIDA
        """
        rol = user.rol if hasattr(user, 'rol') else None
        
        # Obtener fechas CORREGIDAS
        fechas = DashboardRepository.get_fechas_filtro(fecha_inicio, fecha_fin, periodo)
        
        logger.info(f"📊 Dashboard para {rol}: período {fechas['periodo']}, "
                   f"fechas {fechas['fecha_inicio']} - {fechas['fecha_fin']}")

        try:
            if rol == 'Administrador':
                return DashboardService._get_admin_dashboard(fechas, user)
            elif rol == 'Odontologo':
                return DashboardService._get_odontologo_dashboard(user, fechas)
            elif rol == 'Asistente':
                return DashboardService._get_asistente_dashboard(fechas)
            else:
                return DashboardService._get_default_dashboard(fechas, rol)
        except Exception as e:
            logger.error(f"Error obteniendo dashboard para usuario {user.username}: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _calcular_info_periodo(fechas):
        """
        ✅ NUEVA FUNCIÓN: Calcula la información de periodo para mostrar en las tarjetas
        """
        fecha_inicio = fechas['fecha_inicio']
        fecha_fin = fechas['fecha_fin']
        periodo_activo = fechas['periodo']
        
        # Mapeo de meses en español
        MESES_CORTOS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                        'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        MESES_LARGOS = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        # Calcular etiquetas según el periodo
        if periodo_activo == 'hoy' or periodo_activo == 'dia':
            label_periodo = fecha_inicio.strftime('%d %b')
            range_text = f"Hoy {fecha_inicio.strftime('%d/%m/%Y')}"
            
        elif periodo_activo == 'semana' or periodo_activo == 'semana_actual':
            label_periodo = f"{fecha_inicio.strftime('%d')} {MESES_CORTOS[fecha_inicio.month-1]} - {fecha_fin.strftime('%d')} {MESES_CORTOS[fecha_fin.month-1]}"
            range_text = f"Semana del {fecha_inicio.strftime('%d/%m')} al {fecha_fin.strftime('%d/%m')}"
            
        elif periodo_activo == 'mes' or periodo_activo == 'mes_actual':
            mes_nombre = MESES_CORTOS[fecha_inicio.month - 1]
            label_periodo = f"{mes_nombre} {fecha_inicio.year}"
            range_text = f"Mes de {MESES_LARGOS[fecha_inicio.month - 1]} {fecha_inicio.year}"
            
        elif periodo_activo == 'trimestre' or periodo_activo == 'trimestre_actual':
            trimestre = ((fecha_inicio.month - 1) // 3) + 1
            label_periodo = f"Q{trimestre} {fecha_inicio.year}"
            range_text = f"Trimestre {trimestre} ({fecha_inicio.strftime('%d/%m')} - {fecha_fin.strftime('%d/%m')})"
            
        elif periodo_activo == 'anio' or periodo_activo == 'anio_actual':
            label_periodo = f"Año {fecha_inicio.year}"
            range_text = f"Año {fecha_inicio.year}"
            
        else:  # personalizado
            label_periodo = f"{fecha_inicio.strftime('%d')} {MESES_CORTOS[fecha_inicio.month-1]} - {fecha_fin.strftime('%d')} {MESES_CORTOS[fecha_fin.month-1]}"
            range_text = f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}"
        
        return {
            'nombre': periodo_activo,
            'label': label_periodo,
            'descripcion': range_text,
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
        }

    @staticmethod
    def _get_admin_dashboard(fechas, user):
        """📊 Dashboard para Administrador 👔 - SOLO 3 MÉTRICAS PRINCIPALES"""
        from api.appointment.models import EstadoCita
        
        hoy = fechas['hoy']
        inicio_mes = fechas.get('inicio_mes', hoy.replace(day=1))
        fecha_inicio = fechas['fecha_inicio']
        fecha_fin = fechas['fecha_fin']
        
        # ✅✅✅ PERIODOS FIJOS (NO cambian con el filtro) ✅✅✅
        inicio_semana_fija = hoy - timedelta(days=hoy.weekday())  # Lunes de esta semana
        fin_semana_fija = inicio_semana_fija + timedelta(days=6)  # Domingo
        
        # ✅ Calcular información de periodo dinámico
        periodo_info = DashboardService._calcular_info_periodo(fechas)
        
        # Meses en español para labels
        MESES_CORTOS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                        'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

        # ✅ RF-06.1: Métricas Principales - SOLO 3 MÉTRICAS
        metricas = {
            # ✅✅✅ 3 MÉTRICAS PRINCIPALES ✅✅✅
            'pacientes_activos': DashboardRepository.get_pacientes_activos(),
            'citas_hoy': DashboardRepository.get_citas_hoy(hoy),
            'citas_semana': DashboardRepository.get_citas_semana(inicio_semana_fija, fin_semana_fija),
            
            # Métricas secundarias (no se muestran en tarjetas principales)
            'total_pacientes': DashboardRepository.get_total_pacientes(),
            'pacientes_inactivos': DashboardRepository.get_pacientes_inactivos(), 
            'citas_mes': DashboardRepository.get_citas_mes(inicio_mes),
            'citas_asistidas_hoy': DashboardRepository.get_citas_asistidas_hoy(hoy),
            'citas_asistidas_mes': DashboardRepository.get_citas_asistidas_mes(inicio_mes),
            'signos_vitales_hoy': DashboardRepository.get_signos_vitales_hoy(hoy),
            'odontologos_activos': DashboardRepository.get_odontologos_activos(),
            
            # Info de periodo (para los GRÁFICOS - sí afectados por filtro)
            'periodo_activo': fechas['periodo'],
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
            
            # ✅✅✅ NUEVO: Información de periodo para las tarjetas ✅✅✅
            'periodo_info': periodo_info,
            
            # ✅ Info adicional para tooltips
            'info_citas_hoy': {
                'fecha': hoy.isoformat(),
                'descripcion': f"Hoy {hoy.strftime('%d/%m/%Y')}",
                'label': f"{hoy.strftime('%d')} {MESES_CORTOS[hoy.month-1]}"
            },
            'info_semana': {
                'inicio': inicio_semana_fija.isoformat(),
                'fin': fin_semana_fija.isoformat(),
                'descripcion': f"Esta semana: {inicio_semana_fija.strftime('%d/%m')} - {fin_semana_fija.strftime('%d/%m')}",
                'label': f"{inicio_semana_fija.strftime('%d')} {MESES_CORTOS[inicio_semana_fija.month-1]} - {fin_semana_fija.strftime('%d')} {MESES_CORTOS[fin_semana_fija.month-1]}"
            },
            # ✅ Info del periodo del filtro (para "Citas Semana" cuando hay filtro activo)
            'info_periodo_filtro': {
                'descripcion': periodo_info['descripcion'],
                'label': periodo_info['label'],
                'fecha_inicio': fecha_inicio.strftime('%d/%m/%Y'),
                'fecha_fin': fecha_fin.strftime('%d/%m/%Y'),
            }
        }

        # Obtener datos para tablas
        ultimas_citas = DashboardRepository.get_ultimas_citas(5)
        ultimas_citas_data = [
            {
                'id': str(c.id),
                'paciente': c.paciente.nombre_completo if hasattr(c.paciente, 'nombre_completo') 
                        else f"{c.paciente.nombres} {c.paciente.apellidos}",
                'odontologo': f"{c.odontologo.nombres} {c.odontologo.apellidos}" if c.odontologo else 'N/A',
                'fecha': c.fecha.isoformat() if c.fecha else None,
                'hora': str(c.hora_inicio) if c.hora_inicio else None,
                'estado': dict(EstadoCita.choices).get(c.estado, c.estado),
                'motivo': c.motivo_consulta[:50] + '...' if c.motivo_consulta and len(c.motivo_consulta) > 50 
                        else c.motivo_consulta
            }
            for c in ultimas_citas
        ]

        hace_7_dias = fechas.get('hace_7_dias', hoy - timedelta(days=7))
        pacientes_recientes = DashboardRepository.get_pacientes_recientes(hace_7_dias, 5)
        pacientes_recientes_data = [
            {
                'id': str(p.id),
                'nombre': p.nombre_completo if hasattr(p, 'nombre_completo') else f"{p.nombres} {p.apellidos}",
                'cedula': p.cedula_pasaporte or 'N/A',
                'fecha_registro': p.fecha_creacion.isoformat() if p.fecha_creacion else None,
                'telefono': p.telefono or 'N/A'
            }
            for p in pacientes_recientes
        ]

        usuarios = Usuario.objects.filter(
            is_active=True
        ).values(
            'username', 'nombres', 'apellidos', 'rol', 'is_active'
        ).order_by('rol', 'nombres')
        
        usuarios_data = [
            {
                'username': u['username'],
                'nombre': f"{u['nombres']} {u['apellidos']}",
                'rol': u['rol'],
                'activo': u['is_active']
            }
            for u in usuarios
        ]

        # ✅ RF-06.2 y RF-06.3: Gráficos BASADOS EN PERIODO SELECCIONADO
        graficos = {
            'distribucion_estados': DashboardRepository.get_distribucion_citas_por_estado(fecha_inicio, fecha_fin),
            'diagnosticos_frecuentes': DashboardRepository.get_diagnosticos_frecuentes(fecha_inicio, fecha_fin, 8),
            'evolucion_citas': DashboardRepository.get_evolucion_citas_meses(6),
            'citas_por_dia': DashboardRepository.get_citas_por_dia_periodo(fecha_inicio, fecha_fin),
            'citas_por_odontologo': DashboardRepository.get_citas_por_odontologo_periodo(fecha_inicio, fecha_fin),
            'motivos_consulta_frecuentes': DashboardRepository.get_motivos_consulta_frecuentes(fecha_inicio, fecha_fin, 5),
            'distribucion_genero': DashboardRepository.get_distribucion_genero(),
        }

        # ✅ RF-06.3: Secciones para tablas detalladas
        tablas = {
            'ultimas_citas': ultimas_citas_data,
            'pacientes_recientes': pacientes_recientes_data,
            'usuarios_sistema': usuarios_data,
            'top_diagnosticos': DashboardRepository.get_diagnosticos_frecuentes(fecha_inicio, fecha_fin, 10),
        }

        # ✅ RF-06.3: Nueva sección de analíticas UNIFICADA
        analiticas = {
            'diagnosticos_por_diente': DashboardRepository.get_diagnosticos_frecuentes_por_diente(fecha_inicio, fecha_fin, 3),
        }

        return {
            'rol': 'Administrador',
            'metricas': metricas,
            'graficos': graficos,
            'tablas': tablas,
            'analiticas': analiticas,
            'accesos_rapidos': [
                {'accion': 'nueva_cita', 'label': 'Nueva Cita', 'icon': 'calendar-plus'},
                {'accion': 'registrar_paciente', 'label': 'Nuevo Paciente', 'icon': 'user-plus'},
                {'accion': 'odontograma', 'label': 'Odontograma', 'icon': 'tooth'},
                {'accion': 'historial_clinico', 'label': 'Historial', 'icon': 'file-medical'},
            ]
        }

    @staticmethod
    def _get_odontologo_dashboard(user, fechas):
        """🦷 Dashboard para Odontólogo - SOLO 3 MÉTRICAS PRINCIPALES"""
        from api.appointment.models import EstadoCita, Cita
        
        hoy = fechas['hoy']
        inicio_mes = fechas.get('inicio_mes', hoy.replace(day=1))
        fecha_inicio = fechas['fecha_inicio']
        fecha_fin = fechas['fecha_fin']
        
        # ✅✅✅ PERIODOS FIJOS (NO cambian con el filtro) ✅✅✅
        inicio_semana_fija = hoy - timedelta(days=hoy.weekday())  # Lunes de esta semana
        fin_semana_fija = inicio_semana_fija + timedelta(days=6)  # Domingo
        
        # ✅ Calcular información de periodo dinámico
        periodo_info = DashboardService._calcular_info_periodo(fechas)
        
        # Meses en español para labels
        MESES_CORTOS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                        'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

        # Métricas específicas del odontólogo
        metricas = {
            # ✅✅✅ 3 MÉTRICAS PRINCIPALES ✅✅✅
            'pacientes_activos': DashboardRepository.get_pacientes_activos(),
            'citas_hoy': DashboardRepository.get_mis_citas_hoy(user, hoy),
            'citas_semana': DashboardRepository.get_mis_citas_semana(user, inicio_semana_fija, fin_semana_fija),
            
            # Métricas secundarias
            'mis_pacientes_atendidos': DashboardRepository.get_mis_pacientes_atendidos(user),
            'mis_citas_hoy': DashboardRepository.get_mis_citas_hoy(user, hoy),
            'mis_citas_asistidas_hoy': DashboardRepository.get_mis_citas_asistidas_hoy(user, hoy),
            'mis_citas_mes': DashboardRepository.get_mis_citas_mes(user, inicio_mes),
            'pacientes_condiciones_importantes': DashboardRepository.get_pacientes_con_condiciones_importantes(),
            'citas_en_atencion_hoy': Cita.objects.filter(
                odontologo=user,
                fecha=hoy,
                estado=EstadoCita.EN_ATENCION
            ).count(),
            'signos_vitales_hoy': DashboardRepository.get_signos_vitales_hoy(hoy),
            
            # ✅ Información de periodo (para GRÁFICOS - sí afectados por filtro)
            'periodo_activo': fechas['periodo'],
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
            
            # ✅✅✅ NUEVO: Información de periodo para las tarjetas ✅✅✅
            'periodo_info': periodo_info,
            
            # ✅ Métricas generales del sistema (opcional)
            'total_pacientes': DashboardRepository.get_total_pacientes(),
            
            # ✅ Información adicional para el frontend
            'info_citas_hoy': {
                'fecha': hoy.isoformat(),
                'descripcion': f"Hoy {hoy.strftime('%d/%m/%Y')}",
                'label': f"{hoy.strftime('%d')} {MESES_CORTOS[hoy.month-1]}"
            },
            'info_semana': {
                'inicio': inicio_semana_fija.isoformat(),
                'fin': fin_semana_fija.isoformat(),
                'descripcion': f"Esta semana: {inicio_semana_fija.strftime('%d/%m')} - {fin_semana_fija.strftime('%d/%m')}",
                'label': f"{inicio_semana_fija.strftime('%d')} {MESES_CORTOS[inicio_semana_fija.month-1]} - {fin_semana_fija.strftime('%d')} {MESES_CORTOS[fin_semana_fija.month-1]}"
            },
            # ✅ Info del periodo del filtro
            'info_periodo_filtro': {
                'descripcion': periodo_info['descripcion'],
                'label': periodo_info['label'],
                'fecha_inicio': fecha_inicio.strftime('%d/%m/%Y'),
                'fecha_fin': fecha_fin.strftime('%d/%m/%Y'),
            }
        }

        # ✅ Gráficos FILTRADOS por odontólogo (SÍ afectados por filtro)
        graficos = {
            'distribucion_estados': DashboardRepository.get_distribucion_citas_por_estado_odontologo(
                user, fecha_inicio, fecha_fin
            ),
            'diagnosticos_frecuentes': DashboardRepository.get_diagnosticos_frecuentes_odontologo(
                user, fecha_inicio, fecha_fin, 8
            ),
            'evolucion_citas': DashboardRepository.get_evolucion_citas_meses_odontologo(user, 6),
            'citas_por_dia': DashboardRepository.get_citas_por_dia_periodo_odontologo(
                user, fecha_inicio, fecha_fin
            ),
        }

        # ✅ Listas - Convertir QuerySets a listas serializables
        mis_citas_qs = DashboardRepository.get_mis_ultimas_citas(user, 10)
        mis_citas_data = []
        for c in mis_citas_qs:
            mis_citas_data.append({
                'id': str(c.id),
                'paciente': c.paciente.nombre_completo if hasattr(c.paciente, 'nombre_completo') 
                        else f"{c.paciente.nombres} {c.paciente.apellidos}",
                'fecha': c.fecha.isoformat() if c.fecha else None,
                'hora': str(c.hora_inicio) if c.hora_inicio else None,
                'estado': dict(EstadoCita.choices).get(c.estado, c.estado),
                'estado_codigo': c.estado,
                'motivo': (c.motivo_consulta[:50] + '...' 
                        if c.motivo_consulta and len(c.motivo_consulta) > 50 
                        else c.motivo_consulta) if c.motivo_consulta else 'Sin motivo',
            })

        pacientes_condiciones_qs = DashboardRepository.get_pacientes_con_condiciones_importantes_lista(10)
        pacientes_condiciones_data = []
        for p in pacientes_condiciones_qs:
            alergias_list = []
            if hasattr(p, 'anamnesis_general') and p.anamnesis_general:
                if p.anamnesis_general.alergia_antibiotico and p.anamnesis_general.alergia_antibiotico != 'NINGUNA':
                    alergias_list.append(f"Antibiótico: {p.anamnesis_general.alergia_antibiotico}")
                if p.anamnesis_general.alergia_anestesia and p.anamnesis_general.alergia_anestesia != 'NINGUNA':
                    alergias_list.append(f"Anestesia: {p.anamnesis_general.alergia_anestesia}")
            
            pacientes_condiciones_data.append({
                'id': str(p.id),
                'nombre': p.nombre_completo if hasattr(p, 'nombre_completo') 
                        else f"{p.nombres} {p.apellidos}",
                'cedula': p.cedula_pasaporte or 'N/A',
                'alergias': ', '.join(alergias_list) if alergias_list else 'Sin alergias',
                'telefono': p.telefono or 'N/A',
            })

        listas = {
            'mis_citas': mis_citas_data,
            'pacientes_condiciones': pacientes_condiciones_data,
        }

        # ✅ Tablas
        tablas = {
            'mis_citas': mis_citas_data,
            'pacientes_condiciones': pacientes_condiciones_data,
            'top_diagnosticos': DashboardRepository.get_diagnosticos_frecuentes_odontologo(
                user, fecha_inicio, fecha_fin, 10
            ),
        }

        return {
            'rol': 'Odontologo',
            'metricas': metricas,
            'graficos': graficos,
            'tablas': tablas,
            'listas': listas,
            'accesos_rapidos': [
                {'accion': 'registrar_cita', 'label': 'Nueva Cita', 'icon': 'calendar-plus'},
                {'accion': 'iniciar_atencion', 'label': 'Iniciar Atención', 'icon': 'stethoscope'},
                {'accion': 'registrar_anamnesis', 'label': 'Anamnesis', 'icon': 'file-medical'},
                {'accion': 'buscar_paciente', 'label': 'Buscar Paciente', 'icon': 'search'},
            ],
            'usuario': {
                'username': user.username,
                'nombre_completo': f"Dr./Dra. {user.nombres} {user.apellidos}" if hasattr(user, 'nombres') else user.username,
            }
        }

    @staticmethod
    def _get_asistente_dashboard(fechas):
        """👨‍⚕️ Dashboard para Asistente - VERSIÓN CORREGIDA"""
        hoy = fechas['hoy']
        inicio_mes = fechas.get('inicio_mes', hoy.replace(day=1))
        fecha_inicio = fechas['fecha_inicio']
        fecha_fin = fechas['fecha_fin']

        # Métricas del asistente
        metricas = {
            'pacientes_atendidos_hoy': DashboardRepository.get_pacientes_atendidos_hoy(hoy),
            'citas_hoy': DashboardRepository.get_citas_hoy(hoy),
            'citas_programadas_hoy': DashboardRepository.get_citas_programadas_hoy(hoy),
            'citas_confirmadas_hoy': DashboardRepository.get_citas_confirmadas_hoy(hoy),
            'signos_vitales_hoy': DashboardRepository.get_signos_vitales_hoy(hoy),
            'pacientes_nuevos_mes': DashboardRepository.get_pacientes_nuevos_mes(inicio_mes),
            'total_pacientes': DashboardRepository.get_total_pacientes(),
            'pacientes_activos': DashboardRepository.get_pacientes_activos(),
            'periodo_activo': fechas['periodo'],
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
        }

        # ✅ Gráficos para Asistente
        graficos = {
            'distribucion_estados': DashboardRepository.get_distribucion_citas_por_estado(fecha_inicio, fecha_fin),
            'citas_por_dia': DashboardRepository.get_citas_por_dia_periodo(fecha_inicio, fecha_fin),
            'signos_por_hora': DashboardRepository.get_signos_vitales_por_hora(hoy),
            'evolucion_citas': DashboardRepository.get_evolucion_citas_meses(6),
        }

        # ✅ CONVERTIR QuerySets a listas serializables
        citas_del_dia_qs = DashboardRepository.get_ultimas_citas_dia(hoy, 10)
        citas_del_dia_data = []
        for c in citas_del_dia_qs:
            citas_del_dia_data.append({
                'id': str(c.id),
                'paciente': c.paciente.nombre_completo if hasattr(c.paciente, 'nombre_completo') 
                        else f"{c.paciente.nombres} {c.paciente.apellidos}",
                'odontologo': f"{c.odontologo.nombres} {c.odontologo.apellidos}" if c.odontologo else 'N/A',
                'fecha': c.fecha.isoformat() if c.fecha else None,
                'hora': str(c.hora_inicio) if c.hora_inicio else None,
                'estado': dict(EstadoCita.choices).get(c.estado, c.estado),
                'motivo': (c.motivo_consulta[:50] + '...' 
                        if c.motivo_consulta and len(c.motivo_consulta) > 50 
                        else c.motivo_consulta),
            })

        ultimos_signos_qs = DashboardRepository.get_ultimos_signos_vitales(10)
        ultimos_signos_data = []
        for s in ultimos_signos_qs:
            ultimos_signos_data.append({
                'id': str(s.id),
                'paciente': s.paciente.nombre_completo if hasattr(s.paciente, 'nombre_completo')
                        else f"{s.paciente.nombres} {s.paciente.apellidos}",
                'temperatura': s.temperatura or 'N/A',
                'fecha': s.fecha_creacion.isoformat() if s.fecha_creacion else None,
                'registrado_por': f"{s.creado_por.nombres} {s.creado_por.apellidos}" if s.creado_por else 'N/A',
            })

        pacientes_sin_signos_qs = DashboardRepository.get_pacientes_sin_signos_vitales_recientes(7, 10)
        pacientes_sin_signos_data = []
        for p in pacientes_sin_signos_qs:
            pacientes_sin_signos_data.append({
                'id': str(p.id),
                'nombre': p.nombre_completo if hasattr(p, 'nombre_completo')
                        else f"{p.nombres} {p.apellidos}",
                'cedula': p.cedula_pasaporte or 'N/A',
                'telefono': p.telefono or 'N/A',
                'ultima_visita': 'Hace más de 7 días',
            })

        # ✅ Listas serializables
        listas = {
            'citas_del_dia': citas_del_dia_data,
            'ultimos_signos': ultimos_signos_data,
            'pacientes_sin_signos': pacientes_sin_signos_data,
        }

        # ✅ Tablas
        tablas = {
            'citas_del_dia': citas_del_dia_data,
            'ultimos_signos': ultimos_signos_data,
        }

        return {
            'rol': 'Asistente',
            'metricas': metricas,
            'graficos': graficos,
            'tablas': tablas,
            'listas': listas,
            'accesos_rapidos': [
                {'accion': 'registrar_cita', 'label': 'Nueva Cita', 'icon': 'calendar-plus'},
                {'accion': 'registrar_signos', 'label': 'Signos Vitales', 'icon': 'heart-pulse'},
                {'accion': 'confirmar_cita', 'label': 'Confirmar Cita', 'icon': 'check-circle'},
                {'accion': 'registrar_paciente', 'label': 'Nuevo Paciente', 'icon': 'user-plus'},
            ]
        }

    @staticmethod
    def _get_default_dashboard(fechas, rol):
        """Dashboard por defecto"""
        hoy = fechas['hoy']
        
        return {
            'rol': rol or 'Invitado',
            'metricas': {
                'fecha_actual': hoy.isoformat(),
                'periodo_activo': fechas['periodo']
            },
            'mensaje': 'Dashboard de Plexident - Sistema de Gestión Odontológica',
            'timestamp': timezone.now().isoformat()
        }

    # ==================== SERVICIOS ADICIONALES ====================

    @staticmethod
    def get_estadisticas_citas_completas(fecha_inicio, fecha_fin):
        """
        ✅ RF-06.2: Endpoint dedicado para estadísticas de citas
        """
        estadisticas = DashboardRepository.get_estadisticas_detalladas_citas(fecha_inicio, fecha_fin)
        distribucion = DashboardRepository.get_distribucion_citas_por_estado(fecha_inicio, fecha_fin)
        evolucion = DashboardRepository.get_citas_por_dia_periodo(fecha_inicio, fecha_fin)
        
        dias = (fecha_fin - fecha_inicio).days + 1
        promedio = (estadisticas['total'] / dias) if dias > 0 else 0
        
        return {
            'periodo': {
                'fecha_inicio': fecha_inicio.isoformat(),
                'fecha_fin': fecha_fin.isoformat(),
                'total_dias': dias
            },
            'estadisticas': estadisticas,
            'distribucion_estados': distribucion,
            'promedio_diario': round(promedio, 2),
            'evolucion_diaria': evolucion
        }

    @staticmethod
    def get_diagnosticos_frecuentes_data(fecha_inicio, fecha_fin, limit=10):
        """
        ✅ RF-06.3: Obtiene datos para estadísticas de diagnósticos frecuentes
        """
        from api.odontogram.models import DiagnosticoDental
        
        return {
            'periodo': {
                'fecha_inicio': fecha_inicio.isoformat(),
                'fecha_fin': fecha_fin.isoformat()
            },
            'total_diagnosticos_periodo': DiagnosticoDental.objects.filter(
                fecha__date__gte=fecha_inicio,
                fecha__date__lte=fecha_fin,
                activo=True
            ).count(),
            'diagnosticos_frecuentes': DashboardRepository.get_diagnosticos_frecuentes(fecha_inicio, fecha_fin, limit),
            'diagnosticos_por_diente': DashboardRepository.get_diagnosticos_frecuentes_por_diente(fecha_inicio, fecha_fin, 3),
            'metadata': {
                'limit': limit,
                'tipo_analisis': 'diagnosticos_frecuentes'
            }
        }
