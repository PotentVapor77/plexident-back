from django.core.management.base import BaseCommand

from users.models import Usuario

class Command(BaseCommand):
    help = 'Crea un usuario administrador inicial'

    def handle(self, *args, **options):
        # Verificar si ya existe un administrador
        if not Usuario.objects.filter(rol='admin').exists():
            admin = Usuario(
                nombres="Steven",
                apellidos="Sanchez", 
                correo="admin@odontologia.com",
                telefono="1234567890",
                rol="admin",
                status=True
            )
            admin.set_password("admin123")
            admin.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Usuario administrador creado: {admin.username}')
            )
            self.stdout.write(
                self.style.WARNING('🔑 Password: admin123')
            )
            self.stdout.write(
                self.style.WARNING('📧 Email: admin@odontologia.com')
            )
        else:
            self.stdout.write(
                self.style.WARNING('ℹ️ Ya existe un usuario administrador')
            )