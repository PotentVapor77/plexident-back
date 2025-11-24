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


