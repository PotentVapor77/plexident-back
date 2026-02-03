# api/parameters/services/notificacion_service.py
from datetime import datetime, timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from ..repositories.parametro_repository import ParametroRepository
import logging

logger = logging.getLogger(__name__)


class NotificacionService:
    """Servicio para lógica de notificaciones y recordatorios (RF-07.7)"""
    
    @staticmethod
    def calcular_hora_recordatorio(cita_hora: datetime, config=None) -> datetime:
        """
        Calcular cuándo enviar el recordatorio de una cita
        
        Args:
            cita_hora: Fecha y hora de la cita
            config: ConfiguracionNotificaciones object (si None, obtiene del repo)
        
        Returns:
            datetime para enviar recordatorio
        """
        if not config:
            config = ParametroRepository.get_configuracion_notificaciones()
        
        horas_antes = config.recordatorio_citas_horas_antes
        
        # Calcular hora de recordatorio
        hora_recordatorio = cita_hora - timedelta(hours=horas_antes)
        
        # Ajustar a la hora de envío configurada si es para el mismo día
        if hora_recordatorio.date() == timezone.now().date():
            # Combinar fecha con hora de envío configurada
            hora_recordatorio = datetime.combine(
                hora_recordatorio.date(),
                config.hora_envio_diaria
            ).replace(tzinfo=timezone.get_current_timezone())
        
        # Asegurar que no sea en el pasado
        ahora = timezone.now()
        if hora_recordatorio < ahora:
            # Enviar inmediatamente si ya pasó el tiempo ideal
            hora_recordatorio = ahora + timedelta(minutes=5)
        
        return hora_recordatorio
    
    @staticmethod
    def preparar_recordatorio_cita(cita_data: dict, config=None) -> dict:
        """
        Preparar datos para recordatorio de cita
        
        Args:
            cita_data: Diccionario con datos de la cita
            config: ConfiguracionNotificaciones object
        
        Returns:
            Dict con datos preparados para envío
        """
        if not config:
            config = ParametroRepository.get_configuracion_notificaciones()
        
        paciente = cita_data.get('paciente', {})
        fecha_cita = cita_data.get('fecha_hora')
        
        if not fecha_cita:
            raise ValueError("Se requiere fecha_hora para preparar recordatorio")
        
        # Formatear fecha
        if isinstance(fecha_cita, str):
            fecha_cita = datetime.fromisoformat(fecha_cita.replace('Z', '+00:00'))
        
        fecha_formateada = fecha_cita.strftime('%d/%m/%Y')
        hora_formateada = fecha_cita.strftime('%H:%M')
        
        # Preparar contexto para templates
        contexto = {
            'paciente_nombre': paciente.get('nombres', '') + ' ' + paciente.get('apellidos', ''),
            'paciente_telefono': paciente.get('telefono', ''),
            'fecha_cita': fecha_formateada,
            'hora_cita': hora_formateada,
            'clinica_nombre': 'FamySALUD',
            'clinica_telefono': '+593 123456789',
            'clinica_direccion': 'Dirección de la clínica',
            'recordatorio_horas': config.recordatorio_citas_horas_antes,
            'anio_actual': datetime.now().year
        }
        
        return {
            'contexto': contexto,
            'asunto': config.asunto_email_recordatorio,
            'plantilla_sms': config.plantilla_sms.format(**contexto),
            'enviar_email': config.enviar_email,
            'enviar_sms': config.enviar_sms
        }
    
    @staticmethod
    def enviar_email_recordatorio(email_destino: str, datos_recordatorio: dict, config=None):
        """
        Enviar email de recordatorio
        
        Args:
            email_destino: Email del destinatario
            datos_recordatorio: Datos preparados por preparar_recordatorio_cita()
            config: ConfiguracionNotificaciones object
        """
        if not config:
            config = ParametroRepository.get_configuracion_notificaciones()
        
        if not config.enviar_email:
            logger.info("Envío de email deshabilitado en configuración")
            return
        
        try:
            contexto = datos_recordatorio['contexto']
            
            # Contenido de texto plano
            text_content = render_to_string('emails/recordatorio_cita.txt', contexto)
            
            # Contenido HTML
            html_content = render_to_string('emails/recordatorio_cita.html', contexto)
            
            # Crear email
            email = EmailMultiAlternatives(
                subject=datos_recordatorio['asunto'],
                body=text_content,
                from_email=None,  # Usar DEFAULT_FROM_EMAIL de settings
                to=[email_destino]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Enviar
            email.send()
            
            logger.info(f"Email de recordatorio enviado a {email_destino}")
            
        except Exception as e:
            logger.error(f"Error enviando email de recordatorio: {str(e)}")
            raise
    
    @staticmethod
    def enviar_sms_recordatorio(numero_telefono: str, datos_recordatorio: dict, config=None):
        """
        Enviar SMS de recordatorio (implementación básica)
        
        Args:
            numero_telefono: Número de teléfono del destinatario
            datos_recordatorio: Datos preparados por preparar_recordatorio_cita()
            config: ConfiguracionNotificaciones object
        """
        if not config:
            config = ParametroRepository.get_configuracion_notificaciones()
        
        if not config.enviar_sms:
            logger.info("Envío de SMS deshabilitado en configuración")
            return
        
        try:
            # Aquí se integraría con un servicio de SMS como Twilio, MessageBird, etc.
            # Por ahora solo logueamos
            
            mensaje = datos_recordatorio['plantilla_sms']
            
            # Simular envío (en producción se reemplaza por API real)
            logger.info(f"[SMS SIMULADO] Para: {numero_telefono}")
            logger.info(f"[SMS SIMULADO] Mensaje: {mensaje}")
            
            # Ejemplo con Twilio:
            # from twilio.rest import Client
            # client = Client(account_sid, auth_token)
            # message = client.messages.create(
            #     body=mensaje,
            #     from_='+1234567890',
            #     to=numero_telefono
            # )
            
        except Exception as e:
            logger.error(f"Error enviando SMS de recordatorio: {str(e)}")
            raise
    
    @staticmethod
    def enviar_recordatorio_cita(cita_data: dict, config=None):
        """
        Enviar recordatorio de cita por todos los canales configurados
        
        Args:
            cita_data: Datos completos de la cita
            config: ConfiguracionNotificaciones object
        """
        if not config:
            config = ParametroRepository.get_configuracion_notificaciones()
        
        paciente = cita_data.get('paciente', {})
        email_paciente = paciente.get('correo')
        telefono_paciente = paciente.get('telefono')
        
        if not email_paciente and not telefono_paciente:
            logger.warning(f"No hay contacto para enviar recordatorio de cita {cita_data.get('id')}")
            return
        
        # Preparar datos
        datos_recordatorio = NotificacionService.preparar_recordatorio_cita(cita_data, config)
        
        # Enviar por email
        if email_paciente and config.enviar_email:
            try:
                NotificacionService.enviar_email_recordatorio(email_paciente, datos_recordatorio, config)
            except Exception as e:
                logger.error(f"Error enviando email a {email_paciente}: {str(e)}")
        
        # Enviar por SMS
        if telefono_paciente and config.enviar_sms:
            try:
                NotificacionService.enviar_sms_recordatorio(telefono_paciente, datos_recordatorio, config)
            except Exception as e:
                logger.error(f"Error enviando SMS a {telefono_paciente}: {str(e)}")
    
    @staticmethod
    def enviar_email_prueba(email_destino: str, config=None):
        """
        Enviar email de prueba para verificar configuración
        
        Args:
            email_destino: Email para enviar prueba
            config: ConfiguracionNotificaciones object
        """
        if not config:
            config = ParametroRepository.get_configuracion_notificaciones()
        
        try:
            contexto = {
                'fecha_cita': '01/01/2024',
                'hora_cita': '10:00',
                'paciente_nombre': 'Usuario de Prueba',
                'clinica_nombre': 'FamySALUD',
                'clinica_telefono': '+593 123456789',
                'anio_actual': datetime.now().year
            }
            
            # Contenido de texto plano
            text_content = f"""
            PRUEBA DE NOTIFICACIÓN - FamySALUD
            
            Hola {contexto['paciente_nombre']},
            
            Este es un email de prueba para verificar que el sistema de notificaciones está funcionando correctamente.
            
            Si recibes este mensaje, significa que la configuración de emails está correcta.
            
            Fecha de prueba: {contexto['fecha_cita']} a las {contexto['hora_cita']}
            
            Saludos,
            Equipo FamySALUD
            """
            
            # Contenido HTML
            html_content = render_to_string('emails/prueba_notificacion.html', contexto)
            
            # Crear email
            email = EmailMultiAlternatives(
                subject=f"PRUEBA: {config.asunto_email_recordatorio}",
                body=text_content,
                from_email=None,
                to=[email_destino]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Enviar
            email.send()
            
            logger.info(f"Email de prueba enviado a {email_destino}")
            
        except Exception as e:
            logger.error(f"Error enviando email de prueba: {str(e)}")
            raise
    
    @staticmethod
    def obtener_configuracion_notificaciones() -> dict:
        """Obtener configuración de notificaciones para mostrar al usuario"""
        config = ParametroRepository.get_configuracion_notificaciones()
        
        return {
            'recordatorio_citas_horas_antes': config.recordatorio_citas_horas_antes,
            'enviar_email': config.enviar_email,
            'enviar_sms': config.enviar_sms,
            'hora_envio_diaria': config.hora_envio_diaria.strftime('%H:%M'),
            'asunto_email_recordatorio': config.asunto_email_recordatorio,
            'plantilla_sms': config.plantilla_sms
        }
    
    @staticmethod
    def verificar_citas_pendientes_recordatorio():
        """
        Verificar citas que necesitan recordatorio (para ser llamado por un cron job)
        
        Returns:
            Lista de IDs de citas que necesitan recordatorio
        """
        # Esta función sería llamada por un cron job cada hora o día
        
        from api.appointment.models import Cita  # Importar aquí para evitar circular import
        
        config = ParametroRepository.get_configuracion_notificaciones()
        
        if not config.enviar_email and not config.enviar_sms:
            logger.info("Notificaciones deshabilitadas en configuración")
            return []
        
        # Calcular rango de tiempo para recordatorios
        ahora = timezone.now()
        inicio_rango = ahora + timedelta(hours=config.recordatorio_citas_horas_antes)
        fin_rango = inicio_rango + timedelta(hours=1)  # Verificar citas en la próxima hora
        
        # Buscar citas pendientes en ese rango
        citas_pendientes = Cita.objects.filter(
            fecha_hora__gte=inicio_rango,
            fecha_hora__lt=fin_rango,
            estado__in=['programada', 'confirmada'],
            recordatorio_enviado=False
        ).select_related('paciente')
        
        citas_ids = list(citas_pendientes.values_list('id', flat=True))
        
        logger.info(f"Encontradas {len(citas_ids)} citas pendientes de recordatorio")
        
        return citas_ids