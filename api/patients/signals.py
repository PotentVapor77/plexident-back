from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Paciente

@receiver(post_save, sender=Paciente)
def paciente_audit(sender, instance, created, **kwargs):
    if created:
        print(f"[AUDIT] Paciente creado: {instance.nombres} {instance.apellidos}")
    else:
        print(f"[AUDIT] Paciente actualizado: {instance.id_paciente}")
