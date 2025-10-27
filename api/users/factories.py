import factory
from .models import Usuario

class UsuarioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Usuario

    nombres = factory.Faker('first_name')
    apellidos = factory.Faker('last_name')
    telefono = factory.Faker('phone_number')
    correo = factory.Faker('email')
    contrasena_hash = factory.Faker('password', length=12)
    rol = factory.Iterator(['admin', 'odontologo', 'asistente'])
