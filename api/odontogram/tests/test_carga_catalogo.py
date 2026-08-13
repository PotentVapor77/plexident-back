import pytest
from django.core.management import call_command

from api.odontogram.models import (
    AreaAfectada,
    CategoriaDiagnostico,
    Diagnostico,
    DiagnosticoAreaAfectada,
    DiagnosticoAtributoClinico,
    OpcionAtributoClinico,
    TipoAtributoClinico,
)

# Conteos esperados de los CSV en api/odontogram/data
CONTEOS_ESPERADOS = {
    AreaAfectada: 3,
    TipoAtributoClinico: 7,
    OpcionAtributoClinico: 37,
    CategoriaDiagnostico: 4,
    Diagnostico: 22,
    DiagnosticoAreaAfectada: 22,
    DiagnosticoAtributoClinico: 11,
}


@pytest.mark.django_db
def test_carga_csv_carga_todos_los_catalogos():
    """La carga desde CSV inserta todos los registros esperados."""
    call_command('cargar_odontograma_csv', quiet=True)

    for model, esperado in CONTEOS_ESPERADOS.items():
        assert model.objects.count() == esperado, (
            f"{model.__name__}: se esperaban {esperado} registros, "
            f"se encontraron {model.objects.count()}"
        )


@pytest.mark.django_db
def test_carga_csv_idempotente_no_duplica():
    """Ejecutar la carga dos veces no debe duplicar registros."""
    call_command('cargar_odontograma_csv', quiet=True)
    conteo_primera = {model: model.objects.count() for model in CONTEOS_ESPERADOS}

    call_command('cargar_odontograma_csv', quiet=True)
    conteo_segunda = {model: model.objects.count() for model in CONTEOS_ESPERADOS}

    for model in CONTEOS_ESPERADOS:
        assert conteo_segunda[model] == conteo_primera[model] == CONTEOS_ESPERADOS[model], (
            f"{model.__name__}: se duplicaron registros "
            f"({conteo_primera[model]} -> {conteo_segunda[model]})"
        )
