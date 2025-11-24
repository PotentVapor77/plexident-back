from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Usuario
from django.contrib.auth.models import Group

@receiver(post_save, sender=Usuario)
def usuario_audit(sender, instance, created, **kwargs):
    if created:
        print(f"[AUDIT] Usuario creado: {instance.nombres} {instance.apellidos} (ID: {instance.id})")
    else:
        print(f"[AUDIT] Usuario actualizado: {instance.id} - {instance.username}")



@receiver(post_save, sender=Usuario)
def asignar_grupo_por_rol(sender, instance, created, **kwargs):
    if created:
        try:
            # Asignar grupo basado en el rol
            if instance.rol == 'admin':
                grupo = Group.objects.get(name='Administradores')
            elif instance.rol == 'odontologo':
                grupo = Group.objects.get(name='Odontólogos')
            elif instance.rol == 'asistente':
                grupo = Group.objects.get(name='Asistentes')
            else:
                return
                
            instance.groups.add(grupo)
            print(f"✅ Usuario {instance.username} asignado al grupo: {grupo.name}")
        except Group.DoesNotExist:
            print("⚠️ Los grupos no existen. Crea los grupos en el Admin primero.")