
from datetime import timezone
from functools import cache
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from api.odontogram.models import (
    Paciente,
    Diente,
    HistorialOdontograma,
)
User = get_user_model()


class OdontogramaEstadoDienteService:
    @transaction.atomic
    def marcar_diente_ausente(self, paciente_id: str, codigo_fdi: str, odontologo_id: int) -> Diente:
        try:
            diente = Diente.objects.select_for_update().get(
                paciente_id=paciente_id, 
                codigo_fdi=codigo_fdi
            )
            odontologo = User.objects.get(id=odontologo_id)
        except (Diente.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Diente o odontólogo no encontrado")

        paciente_id = str(diente.paciente.id)
        
        # 1. Marcar como ausente
        diente.ausente = True
        diente.save()

        # 2. SIEMPRE solo registro simple (SIN snapshot)
        print(f"[CONTEXTO] Diente ausente marcado - solo registro simple para paciente {paciente_id}")
        HistorialOdontograma.objects.create(
            diente=diente,
            tipo_cambio=HistorialOdontograma.TipoCambio.DIENTE_MARCADO_AUSENTE,
            descripcion=f"Diente {codigo_fdi} marcado como ausente",
            odontologo=odontologo,
            datos_anteriores={'codigo_fdi': codigo_fdi, 'ausente_anterior': False},
            datos_nuevos={'ausente': True},
            fecha=timezone.now(),
        )

        # 3. Invalidar caché (SIN snapshot)
        cache_key = f"odontograma:completo:{paciente_id}"
        cache.delete(cache_key)

        return diente
