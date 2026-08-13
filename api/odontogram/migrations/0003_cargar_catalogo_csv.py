from django.core.management import call_command
from django.db import connection, migrations


def cargar_catalogo_csv(apps, schema_editor):
    """Carga el catálogo del odontograma desde los CSV de api/odontogram/data.

    Idempotente: usa get_or_create, por lo que re-ejecutar no duplica registros.
    Se omite en bases de datos de tests para no interferir con los fixtures.
    """
    if connection.settings_dict.get('NAME', '').startswith('test_'):
        return
    call_command('cargar_odontograma_csv', quiet=True)


class Migration(migrations.Migration):

    dependencies = [
        ('odontogram', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(cargar_catalogo_csv, migrations.RunPython.noop),
    ]
