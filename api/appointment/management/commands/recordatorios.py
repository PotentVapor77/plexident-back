from django.core.management.base import BaseCommand
from appointment.services.appointment_service import RecordatorioService

class Command(BaseCommand):
    help = 'Envía recordatorios automáticos de citas (WhatsApp y Email)'

    def add_arguments(self, parser):
        parser.add_argument('--horas', type=int, default=24, help='Horas antes (default: 24)')
        parser.add_argument('--tipo', type=str, default='WHATSAPP', 
                          choices=['WHATSAPP', 'EMAIL'],
                          help='Tipo de recordatorio (WHATSAPP o EMAIL)')
        parser.add_argument('--destinatario', type=str, default='PACIENTE',
                          choices=['PACIENTE', 'ODONTOLOGO', 'AMBOS'],
                          help='Destinatario del recordatorio')

    def handle(self, *args, **options):
        horas = options['horas']
        tipo = options['tipo']
        destinatario = options['destinatario']
        
        resultado = RecordatorioService.enviar_recordatorios_automaticos(
            horas, tipo, destinatario
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'📊 RESULTADOS RECORDATORIOS:\n'
                f'   📋 Total citas encontradas: {resultado["total_citas"]}\n'
                f'   ✅ Enviados exitosamente: {resultado["enviados"]}\n'
                f'   ❌ Errores: {resultado["errores"]}\n'
                f'   🕐 Horas antes: {horas}\n'
                f'   📨 Tipo: {tipo}\n'
                f'   👤 Destinatario: {destinatario}'
            )
        )
        
        # Mostrar detalles si hay errores
        if resultado['errores'] > 0:
            self.stdout.write(self.style.WARNING('\n📝 Detalles de errores:'))
            for detalle in resultado['detalles']:
                if not detalle['exito']:
                    self.stdout.write(f"   • Cita {detalle['cita_id']}: {detalle['mensaje']}")