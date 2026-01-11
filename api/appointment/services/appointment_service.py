# api/appointment/services/appointment_service.py
import logging
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import requests
import re
from api.appointment.serializers import RecordatorioCitaSerializer
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string

from django.conf import settings

from ..models import Cita, EstadoCita
from ..repositories import CitaRepository, HorarioAtencionRepository, RecordatorioCitaRepository

logger = logging.getLogger(__name__)

class CitaService:
    """Servicio con lógica de negocio para citas"""
    
    @staticmethod
    def obtener_todas_citas(filtros=None):
        """Obtiene todas las citas con filtros opcionales"""
        return CitaRepository.obtener_todas(filtros)
    
    @staticmethod
    def obtener_cita_por_id(cita_id):
        """Obtiene una cita por ID"""
        return CitaRepository.obtener_por_id(cita_id)
    
    @staticmethod
    def obtener_citas_por_fecha_y_odontologo(fecha, odontologo_id):
        """Obtiene las citas de un odontólogo en una fecha"""
        return CitaRepository.obtener_por_fecha_y_odontologo(fecha, odontologo_id)
    
    @staticmethod
    def obtener_citas_por_semana(fecha_inicio, odontologo_id=None):
        """Obtiene citas de una semana"""
        return CitaRepository.obtener_por_semana(fecha_inicio, odontologo_id)
    
    @staticmethod
    def obtener_citas_por_paciente(paciente_id):
        """Obtiene todas las citas de un paciente"""
        return CitaRepository.obtener_por_paciente(paciente_id)
    
    @staticmethod
    @transaction.atomic
    def crear_cita(data):
        """Crea una nueva cita con validaciones"""
        # Calcular hora_fin
        hora_inicio_dt = datetime.combine(datetime.today(), data['hora_inicio'])
        hora_fin_dt = hora_inicio_dt + timedelta(minutes=data['duracion'])
        data['hora_fin'] = hora_fin_dt.time()
        
        # Verificar disponibilidad
        disponible, cita_conflicto = CitaRepository.verificar_disponibilidad(
            data['odontologo'].id,
            data['fecha'],
            data['hora_inicio'],
            data['hora_fin']
        )
        
        if not disponible:
            raise ValidationError(
                f"El odontólogo ya tiene una cita de {cita_conflicto.hora_inicio} a {cita_conflicto.hora_fin}"
            )
        
        # Crear la cita
        cita = CitaRepository.crear(data)
        return cita
    
    @staticmethod
    @transaction.atomic
    def actualizar_cita(cita_id, data):
        """Actualiza una cita existente"""
        cita = CitaRepository.obtener_por_id(cita_id)
        
        if not cita:
            raise ValidationError("Cita no encontrada")
        
        if not cita.puede_ser_cancelada:
            raise ValidationError("Esta cita no puede ser modificada")
        
        # Si se cambia la fecha u hora, verificar disponibilidad
        if 'fecha' in data or 'hora_inicio' in data or 'duracion' in data:
            fecha = data.get('fecha', cita.fecha)
            hora_inicio = data.get('hora_inicio', cita.hora_inicio)
            duracion = data.get('duracion', cita.duracion)
            
            hora_inicio_dt = datetime.combine(datetime.today(), hora_inicio)
            hora_fin_dt = hora_inicio_dt + timedelta(minutes=duracion)
            hora_fin = hora_fin_dt.time()
            
            odontologo_id = data.get('odontologo', cita.odontologo).id
            
            disponible, cita_conflicto = CitaRepository.verificar_disponibilidad(
                odontologo_id,
                fecha,
                hora_inicio,
                hora_fin,
                excluir_cita_id=cita_id
            )
            
            if not disponible:
                raise ValidationError(
                    f"El odontólogo ya tiene una cita de {cita_conflicto.hora_inicio} a {cita_conflicto.hora_fin}"
                )
            
            data['hora_fin'] = hora_fin
        
        return CitaRepository.actualizar(cita, data)
    
    @staticmethod
    @transaction.atomic
    def cancelar_cita(cita_id, motivo, usuario):
        """Cancela una cita"""
        cita = CitaRepository.obtener_por_id(cita_id)
        
        if not cita:
            raise ValidationError("Cita no encontrada")
        
        # ✅ MEJORA: Loggear el estado actual para diagnóstico
        logger = logging.getLogger(__name__)
        logger.info(f"Intentando cancelar cita {cita_id} con estado actual: {cita.estado}")
        
        # ✅ CORRECCIÓN: Usar la propiedad del modelo directamente
        if not cita.puede_ser_cancelada:
            raise ValidationError(
                f"Esta cita no puede ser cancelada (estado actual: {cita.estado})"
            )
        
        data = {
            'estado': EstadoCita.CANCELADA,
            'motivo_cancelacion': motivo,
            'fecha_cancelacion': timezone.now(),
            'cancelada_por': usuario
        }
        
        return CitaRepository.actualizar(cita, data)
    
    @staticmethod
    @transaction.atomic
    def reprogramar_cita(cita_id, nueva_fecha, nueva_hora_inicio, usuario):
        """Reprograma una cita creando una nueva"""
        cita = CitaRepository.obtener_por_id(cita_id)
        
        if not cita:
            raise ValidationError("Cita no encontrada")
        
        if not cita.puede_ser_cancelada:
            raise ValidationError("Esta cita no puede ser reprogramada")
        
        # Calcular hora_fin para nueva cita
        hora_inicio_dt = datetime.combine(datetime.today(), nueva_hora_inicio)
        hora_fin_dt = hora_inicio_dt + timedelta(minutes=cita.duracion)
        hora_fin = hora_fin_dt.time()
        
        # Verificar disponibilidad (excluir la cita original si tiene el mismo día/hora)
        disponible, cita_conflicto = CitaRepository.verificar_disponibilidad(
            cita.odontologo.id,
            nueva_fecha,
            nueva_hora_inicio,
            hora_fin,
            excluir_cita_id=cita_id
        )
        
        if not disponible:
            raise ValidationError(
                f"El odontólogo ya tiene una cita de {cita_conflicto.hora_inicio} a {cita_conflicto.hora_fin}"
            )
        
        # ✅ CORRECCIÓN CRÍTICA: Marcar cita actual como reprogramada y desactivarla
        CitaRepository.actualizar(cita, {
            'estado': EstadoCita.REPROGRAMADA,
            'activo': False  # Desactivar la cita original
        })
        
        # ✅ CORRECCIÓN CRÍTICA: Crear nueva cita con estado REPROGRAMADA (no PROGRAMADA)
        nueva_cita_data = {
            'paciente': cita.paciente,
            'odontologo': cita.odontologo,
            'fecha': nueva_fecha,
            'hora_inicio': nueva_hora_inicio,
            'hora_fin': hora_fin,
            'duracion': cita.duracion,
            'tipo_consulta': cita.tipo_consulta,
            'motivo_consulta': cita.motivo_consulta,
            'observaciones': f"Reprogramada desde {cita.fecha} {cita.hora_inicio}. {cita.observaciones}",
            'cita_original': cita,
            'estado': EstadoCita.REPROGRAMADA,  # ✅ CAMBIO AQUÍ: Estado REPROGRAMADA
            'activo': True
        }
        
        nueva_cita = CitaRepository.crear(nueva_cita_data)
        
        # ✅ Asegurar que el estado display sea correcto
        nueva_cita.estado = EstadoCita.REPROGRAMADA
        nueva_cita.save()
        
        return nueva_cita
    
    @staticmethod
    @transaction.atomic
    def cambiar_estado_cita(cita_id, nuevo_estado):
        """Cambia el estado de una cita"""
        cita = CitaRepository.obtener_por_id(cita_id)
        
        if not cita:
            raise ValidationError("Cita no encontrada")
        
        data = {'estado': nuevo_estado}
        
        if nuevo_estado == EstadoCita.ASISTIDA:
            data['fecha_atencion'] = timezone.now()
        
        return CitaRepository.actualizar(cita, data)
    
    @staticmethod
    def obtener_horarios_disponibles(odontologo_id, fecha, duracion=30):
        """Obtiene horarios disponibles para un odontólogo en una fecha"""
        dia_semana = fecha.weekday()
        
        # Obtener horarios de atención
        horarios = HorarioAtencionRepository.obtener_por_odontologo_y_dia(
            odontologo_id, dia_semana
        )
        
        if not horarios:
            return []
        
        # Obtener citas ya programadas (solo activas)
        citas_programadas = CitaRepository.obtener_por_fecha_y_odontologo(
            fecha, odontologo_id
        ).filter(activo=True)
        
        horarios_disponibles = []
        
        for horario in horarios:
            hora_actual = horario.hora_inicio
            
            while hora_actual < horario.hora_fin:
                hora_actual_dt = datetime.combine(datetime.today(), hora_actual)
                hora_fin_dt = hora_actual_dt + timedelta(minutes=duracion)
                hora_fin = hora_fin_dt.time()
                
                if hora_fin > horario.hora_fin:
                    break
                
                # Verificar conflictos
                hay_conflicto = False
                for cita in citas_programadas:
                    if (hora_actual < cita.hora_fin and hora_fin > cita.hora_inicio):
                        hay_conflicto = True
                        break
                
                if not hay_conflicto:
                    horarios_disponibles.append({
                        'hora_inicio': hora_actual.strftime('%H:%M'),
                        'hora_fin': hora_fin.strftime('%H:%M')
                    })
                
                hora_actual_dt = hora_actual_dt + timedelta(minutes=duracion)
                hora_actual = hora_actual_dt.time()
        
        return horarios_disponibles
    
    @staticmethod
    def eliminar_cita(cita_id):
        """Elimina lógicamente una cita"""
        cita = CitaRepository.obtener_por_id(cita_id)
        
        if not cita:
            raise ValidationError("Cita no encontrada")
        
        return CitaRepository.eliminar_logico(cita)








class HorarioAtencionService:
    """Servicio para horarios de atención"""
    
    @staticmethod
    def obtener_horarios_por_odontologo(odontologo_id):
        """Obtiene todos los horarios de un odontólogo"""
        return HorarioAtencionRepository.obtener_todos_por_odontologo(odontologo_id)
    
    @staticmethod
    def obtener_horario_por_id(horario_id):
        """Obtiene un horario por ID"""
        return HorarioAtencionRepository.obtener_por_id(horario_id)
    
    @staticmethod
    @transaction.atomic
    def crear_horario(data):
        """Crea un nuevo horario de atención"""
        return HorarioAtencionRepository.crear(data)
    
    @staticmethod
    @transaction.atomic
    def actualizar_horario(horario_id, data):
        """Actualiza un horario existente"""
        horario = HorarioAtencionRepository.obtener_por_id(horario_id)
        
        if not horario:
            raise ValidationError("Horario no encontrado")
        
        return HorarioAtencionRepository.actualizar(horario, data)
    
    @staticmethod
    @transaction.atomic
    def eliminar_horario(horario_id):
        """Elimina lógicamente un horario"""
        horario = HorarioAtencionRepository.obtener_por_id(horario_id)
        
        if not horario:
            raise ValidationError("Horario no encontrado")
        
        return HorarioAtencionRepository.eliminar_logico(horario)




class RecordatorioService:
    """Servicio COMPLETO para recordatorios manuales y automáticos."""

    @staticmethod
    @transaction.atomic
    def enviar_recordatorio_manual(cita_id: str, tipo_recordatorio: str = "EMAIL", 
                                destinatario: str = "PACIENTE", 
                                mensaje: str = "") -> dict:
        """Envío manual desde frontend. Permite múltiples recordatorios."""
        cita = CitaRepository.obtener_por_id(cita_id)
        if not cita:
            raise ValidationError("Cita no encontrada")
        
        # Verificar puede enviar
        if not cita.activo:
            raise ValidationError("La cita no está activa")
        
        # ❌ ELIMINAR esta validación para permitir múltiples recordatorios
        # if cita.recordatorio_enviado:
        #     raise ValidationError("La cita ya tiene un recordatorio enviado")
        
        if cita.estado not in (EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA):
            raise ValidationError("Solo las citas PROGRAMADAS o CONFIRMADAS permiten recordatorios")
        
        fecha_hora = timezone.make_aware(datetime.combine(cita.fecha, cita.hora_inicio))
        if fecha_hora <= timezone.now():
            raise ValidationError("No se puede enviar recordatorio para una cita pasada")
        
        # Enviar notificación por EMAIL
        exito, mensaje_envio = RecordatorioService._enviar_notificacion(
            cita, tipo_recordatorio, destinatario, mensaje
        )
        
        # Crear registro
        recordatorio_data = {
            'cita': cita,
            'destinatario': destinatario,
            'tipo_recordatorio': tipo_recordatorio,
            'fecha_envio': timezone.now(),
            'enviado_exitosamente': exito,
            'mensaje': mensaje_envio if exito else "",
            'error': "" if exito else mensaje_envio
        }
        recordatorio = RecordatorioCitaRepository.crear(recordatorio_data)
        
        # ❌ OPCIONAL: Ya no actualizar recordatorio_enviado, o hacerlo de otra forma
        # Solo actualizar la fecha del último recordatorio
        if exito:
            CitaRepository.actualizar(cita, {
                'fecha_recordatorio': timezone.now()  # Solo actualizar fecha
            })
        
        return {
            'exito': exito,
            'mensaje': "✅ Recordatorio enviado exitosamente" if exito else f"❌ Error: {mensaje_envio}",
            'recordatorio': RecordatorioCitaSerializer(recordatorio).data
        }
    # Añade este método en la clase RecordatorioService, justo después de los métodos _crear_html_email_paciente y _crear_html_email_odontologo:

    @staticmethod
    def _enviar_email_html(destinatario, asunto, html_content):
        """Envía email HTML usando Django"""
        try:
            email = EmailMultiAlternatives(
                subject=asunto,
                body='Por favor, vea este mensaje en un cliente de correo que soporte HTML.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[destinatario]
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            
            logger.info(f"Email HTML enviado a {destinatario}")
            return True, "Email enviado correctamente"
        except Exception as e:
            logger.error(f"Error enviando email HTML a {destinatario}: {str(e)}")
            
            # Fallback texto plano
            try:
                import re
                text_content = re.sub('<[^<]+?>', '', html_content).strip()
                send_mail(
                    asunto,
                    text_content,
                    settings.DEFAULT_FROM_EMAIL,
                    [destinatario],
                    fail_silently=False
                )
                logger.info(f"Email texto enviado a {destinatario} (respaldo)")
                return True, "Email enviado correctamente (texto)"
            except Exception as e2:
                logger.error(f"Error enviando email texto a {destinatario}: {str(e2)}")
                return False, f"Error enviando email: {str(e)}"

    @staticmethod
    def enviar_recordatorios_automaticos(horas_antes: int = 24) -> int:
        """Para CRON/Celery - Envía recordatorios automáticos."""
        citas = CitaRepository.obtener_citas_pendientes_recordatorio()
        contador = 0
        
        for cita in citas:
            try:
                # Verificar si está en la ventana temporal
                if RecordatorioService._debe_enviar_auto(cita, horas_antes):
                    resultado = RecordatorioService.enviar_recordatorio_manual(
                        str(cita.id),
                        tipo_recordatorio=getattr(settings, 'RECORDATORIO_TIPO_DEFAULT', 'EMAIL'),
                        destinatario=getattr(settings, 'RECORDATORIO_ENVIAR_A', 'PACIENTE')
                    )
                    if resultado['exito']:
                        contador += 1
            except Exception as e:
                logger.error(f"Error enviando recordatorio automático cita {cita.id}: {str(e)}")
                continue
        
        logger.info(f"Recordatorios automáticos enviados: {contador}/{len(citas)}")
        return contador

    @staticmethod
    @transaction.atomic
    def crear_recordatorio(cita, tipo_recordatorio, mensaje, destinatario="PACIENTE"):
        """Crea un recordatorio para una cita"""
        data = {
            'cita': cita,
            'destinatario': destinatario,
            'tipo_recordatorio': tipo_recordatorio,
            'fecha_envio': timezone.now(),
            'mensaje': mensaje,
            'enviado_exitosamente': False
        }
        
        return RecordatorioCitaRepository.crear(data)
    
    @staticmethod
    def obtener_recordatorios_por_cita(cita_id):
        """Obtiene todos los recordatorios de una cita"""
        return RecordatorioCitaRepository.obtener_por_cita(cita_id)

    # ========================================================================
    # MÉTODOS PRIVADOS
    # ========================================================================
    
    @staticmethod
    def _debe_enviar_auto(cita: Cita, horas_antes: int) -> bool:
        """Verifica ventana temporal automática."""
        fecha_hora = timezone.make_aware(datetime.combine(cita.fecha, cita.hora_inicio))
        ahora = timezone.now()
        inicio = fecha_hora - timedelta(hours=horas_antes)
        fin = fecha_hora - timedelta(hours=horas_antes - 1)
        return inicio <= ahora <= fin
    
    @staticmethod
    def _enviar_notificacion(cita: Cita, tipo: str, destinatario: str = "PACIENTE", 
                           mensaje: str = "") -> tuple[bool, str]:
        """
        Envía notificación - Solo Email con HTML
        """
        if tipo != 'EMAIL':
            return False, "Solo se permite el tipo EMAIL"
        
        # Validar destinatario
        if destinatario == "PACIENTE":
            contacto_email = cita.paciente.correo
            if not contacto_email:
                return False, "Paciente no tiene email configurado"
            
            html_content = RecordatorioService._crear_html_email_paciente(cita, mensaje)
            asunto = f"🦷 FamySALUD - Recordatorio de Cita para {cita.fecha.strftime('%d/%m/%Y')}"
            
            return RecordatorioService._enviar_email_html(contacto_email, asunto, html_content)
        
        elif destinatario == "ODONTOLOGO":
            contacto_email = cita.odontologo.correo
            if not contacto_email:
                return False, "Odontólogo no tiene email configurado"
            
            html_content = RecordatorioService._crear_html_email_odontologo(cita, mensaje)
            asunto = f"🦷 FamySALUD - Agenda del Día {cita.fecha.strftime('%d/%m/%Y')}"
            
            return RecordatorioService._enviar_email_html(contacto_email, asunto, html_content)
        
        elif destinatario == "AMBOS":
            # Enviar a ambos
            resultados = []
            exito_total = True
            
            # Enviar al paciente
            if cita.paciente.correo:
                html_paciente = RecordatorioService._crear_html_email_paciente(cita, mensaje)
                asunto_paciente = f"🦷 FamySALUD - Recordatorio de Cita para {cita.fecha.strftime('%d/%m/%Y')}"
                exito_paciente, msg_paciente = RecordatorioService._enviar_email_html(
                    cita.paciente.correo, asunto_paciente, html_paciente
                )
                resultados.append(f"Paciente: {'✅' if exito_paciente else '❌'}")
                exito_total = exito_total and exito_paciente
            
            # Enviar al odontólogo
            if cita.odontologo.correo:
                html_odontologo = RecordatorioService._crear_html_email_odontologo(cita, mensaje)
                asunto_odontologo = f"🦷 FamySALUD - Agenda del Día {cita.fecha.strftime('%d/%m/%Y')}"
                exito_odontologo, msg_odontologo = RecordatorioService._enviar_email_html(
                    cita.odontologo.correo, asunto_odontologo, html_odontologo
                )
                resultados.append(f"Odontólogo: {'✅' if exito_odontologo else '❌'}")
                exito_total = exito_total and exito_odontologo
            
            mensaje = f"Enviado a ambos: {', '.join(resultados)}"
            
            # Si al menos uno se envió, consideramos éxito parcial
            if cita.paciente.correo or cita.odontologo.correo:
                return exito_total, mensaje
            else:
                return False, "Ningún destinatario tiene email configurado"
        
        return False, f"Destinatario '{destinatario}' no válido"

    @staticmethod
    def _crear_html_email_paciente(cita, mensaje=''):
        """Crea HTML de email para paciente"""
        from datetime import datetime
        
        context = {
            'paciente_nombre': cita.paciente.nombre_completo,
            'fecha': cita.fecha.strftime('%d de %B de %Y'),
            'hora': cita.hora_inicio.strftime('%I:%M %p'),
            'odontologo_nombre': cita.odontologo.get_full_name(),
            'tipo_consulta': cita.get_tipo_consulta_display(),
            'motivo_consulta': cita.motivo_consulta,
            'mensaje': mensaje,
            'current_year': datetime.now().year
        }
        
        try:
            # Usar plantilla con estilos inline
            return render_to_string('emails/paciente_recordatorio_email.html', context)
        except Exception as e:
            logger.error(f"Error renderizando plantilla paciente: {str(e)}")
            # Fallback simple
            return f"""Recordatorio de Cita - FamySALUD

    Estimado/a {cita.paciente.nombre_completo},

    📅 {cita.fecha.strftime('%d/%m/%Y')} - {cita.hora_inicio.strftime('%H:%M')}
    👨‍⚕️ {cita.odontologo.get_full_name()}
    📋 {cita.get_tipo_consulta_display()}

    {mensaje}

    FamySALUD Ecuador"""

    @staticmethod
    def _crear_html_email_odontologo(cita, mensaje=''):
        """Crea HTML de email para odontólogo"""
        from datetime import datetime
        
        # Obtener citas del día
        citas_hoy = Cita.objects.filter(
            odontologo=cita.odontologo,
            fecha=cita.fecha,
            activo=True
        ).exclude(
            estado__in=[EstadoCita.CANCELADA, EstadoCita.REPROGRAMADA]
        ).select_related('paciente').order_by('hora_inicio')
        
        citas_hoy_data = []
        for c in citas_hoy:
            citas_hoy_data.append({
                'hora': c.hora_inicio.strftime('%I:%M %p'),
                'paciente_nombre': c.paciente.nombre_completo,
                'telefono': c.paciente.telefono or 'No especificado',
                'tipo_consulta': c.get_tipo_consulta_display(),
                'motivo': c.motivo_consulta,
                'observaciones': c.observaciones,
                'es_primera_vez': c.tipo_consulta == 'PRIMERA_VEZ',
                'es_urgencia': c.tipo_consulta == 'URGENCIA',
                'duracion': c.duracion
            })
        
        context = {
            'odontologo_nombre': cita.odontologo.get_full_name(),
            'citas_hoy': citas_hoy_data,
            'total_citas': len(citas_hoy_data),
            'citas_confirmadas': citas_hoy.filter(estado=EstadoCita.CONFIRMADA).count(),
            'citas_pendientes': citas_hoy.filter(estado=EstadoCita.PROGRAMADA).count(),
            'primera_vez': citas_hoy.filter(tipo_consulta='PRIMERA_VEZ').count(),
            'mensaje': mensaje,
            'current_year': datetime.now().year,
            'fecha_hoy': cita.fecha.strftime('%d de %B de %Y')
        }
        
        try:
            # Usar plantilla con estilos inline
            return render_to_string('emails/odontologo_recordatorio_email.html', context)
        except Exception as e:
            logger.error(f"Error renderizando plantilla odontólogo: {str(e)}")
            # Fallback simple
            return f"""Agenda del Día - FamySALUD

    Dr. {cita.odontologo.get_full_name()},

    Hoy {cita.fecha.strftime('%d/%m/%Y')}: {len(citas_hoy_data)} citas

    {mensaje}

    FamySALUD"""