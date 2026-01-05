from typing import List, Dict, Any, Optional
import uuid
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from api.odontogram.models import (
    Paciente,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
)
from django.db.models import Prefetch

User = get_user_model()



class OdontogramaReadService:
    def obtener_odontograma_completo(self, paciente_id: str) -> Dict[str, Any]:
        """
        Obtiene el odontograma completo de un paciente
        OPTIMIZADO con prefetch_related anidado y caché
        """
        # 1. Intentar obtener del caché primero
        cache_key = f"odontograma:completo:{paciente_id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data

        # 2. Si no hay caché, consultar BD
        try:
            paciente = Paciente.objects.get(id=paciente_id)
        except Paciente.DoesNotExist:
            raise ValidationError("Paciente no encontrado")

        odontograma_data = {}

        # 3. Prefetch anidado profundo
        dientes = (
            Diente.objects.filter(paciente=paciente)
            .prefetch_related(
                Prefetch(
                    "superficies",
                    queryset=SuperficieDental.objects.prefetch_related(
                        Prefetch(
                            "diagnosticos",
                            queryset=DiagnosticoDental.objects.filter(activo=True)
                            .select_related(
                                "diagnostico_catalogo",
                                "diagnostico_catalogo__categoria",
                                "odontologo",
                            )
                            .prefetch_related(
                                "diagnostico_catalogo__areas_relacionadas__area"
                            ),
                        )
                    ),
                )
            )
            .order_by("codigo_fdi")
        )

        # 4. Construir estructura de datos
        for diente in dientes:
            codigo_fdi = diente.codigo_fdi
            odontograma_data[codigo_fdi] = {}

            for superficie in diente.superficies.all():
                odontograma_data[codigo_fdi][superficie.nombre] = []

                for diag_dental in superficie.diagnosticos.all():
                    odontograma_data[codigo_fdi][superficie.nombre].append(
                        {
                            "id": str(diag_dental.id),
                            "procedimientoId": diag_dental.diagnostico_catalogo.key,
                            "nombre": diag_dental.diagnostico_catalogo.nombre,
                            "siglas": diag_dental.diagnostico_catalogo.siglas,
                            "colorHex": diag_dental.diagnostico_catalogo.simbolo_color,
                            "secondaryOptions": diag_dental.atributos_clinicos,
                            "descripcion": diag_dental.descripcion,
                            "afectaArea": list(
                                diag_dental.diagnostico_catalogo.areas_relacionadas.values_list(
                                    "area__key", flat=True
                                )
                            ),
                            "estado_tratamiento": diag_dental.estado_tratamiento,
                            "prioridad": diag_dental.prioridad_efectiva,
                            "categoria_nombre": diag_dental.diagnostico_catalogo.categoria.nombre,
                            "categoria_color_key": diag_dental.diagnostico_catalogo.categoria.color_key,
                            "prioridadKey": diag_dental.diagnostico_catalogo.categoria.prioridad_key,
                            "fecha": diag_dental.fecha.isoformat(),
                            "odontologo": diag_dental.odontologo.get_full_name(),
                        }
                    )

        # 5. Construir respuesta
        result = {
            "paciente_id": str(paciente.id),
            "paciente_nombre": f"{paciente.nombres} {paciente.apellidos}",
            "odontograma_data": odontograma_data,
            "fecha_obtension": timezone.now().isoformat(),
        }

        # 6. Guardar en caché por 5 minutos
        cache.set(cache_key, result, timeout=300)

        return result

    
    def obtener_diagnosticos_paciente(
        self, paciente_id: str, estado_tratamiento: Optional[str] = None
    ) -> List[DiagnosticoDental]:
        """
        Obtiene todos los diagnósticos de un paciente
        opcionalmente filtrados por estado
        """
        try:
            paciente = Paciente.objects.get(id=paciente_id)
        except Paciente.DoesNotExist:
            return []

        # Obtener todos los diagnósticos del paciente
        diagnosticos = DiagnosticoDental.objects.filter(
            superficie__diente__paciente=paciente, activo=True
        ).select_related("diagnostico_catalogo", "diagnostico_catalogo__categoria", "superficie__diente", "odontologo")

        if estado_tratamiento:
            diagnosticos = diagnosticos.filter(estado_tratamiento=estado_tratamiento)

        return list(diagnosticos)