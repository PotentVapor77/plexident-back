
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
    def marcar_diente_ausente(
        self, paciente_id: str, codigo_fdi: str, odontologo_id: int
    ) -> Diente:
        """
        Marca un diente como ausente y registra en historial
        """
        try:
            paciente = Paciente.objects.get(id=paciente_id)
            odontologo = User.objects.get(id=odontologo_id)
        except (Paciente.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Paciente u odontólogo no encontrado")

        diente, _ = Diente.objects.get_or_create(
            paciente=paciente, codigo_fdi=codigo_fdi
        )

        # Cambiar estado
        era_ausente = diente.ausente
        diente.ausente = True
        diente.save()

        # Crear historial
        if not era_ausente:
            HistorialOdontograma.objects.create(
                diente=diente,
                tipo_cambio=HistorialOdontograma.TipoCambio.DIENTE_MARCADO_AUSENTE,
                descripcion=f"Diente {codigo_fdi} marcado como ausente",
                odontologo=odontologo,
                datos_nuevos={"ausente": True},
            )

        return diente