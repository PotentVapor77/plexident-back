# api/odontogram/management/commands/agregar_diagnostico_movilidad.py
"""
Comando Django para agregar el diagnóstico de Movilidad Dental
Uso: python manage.py agregar_diagnostico_movilidad
"""

from django.core.management.base import BaseCommand
from api.odontogram.models import (
    Diagnostico, 
    CategoriaDiagnostico, 
    TipoAtributoClinico,
    DiagnosticoAtributoClinico
)


class Command(BaseCommand):
    help = 'Agrega el diagnóstico de Movilidad Dental a la categoría Patología Activa'

    def handle(self, *args, **options):
        # Verificar si ya existe
        if Diagnostico.objects.filter(key='movilidad_dental').exists():
            self.stdout.write(
                self.style.WARNING('⚠️  El diagnóstico "movilidad_dental" ya existe')
            )
            return

        try:
            # Obtener la categoría Patología Activa
            categoria = CategoriaDiagnostico.objects.get(key='patologia_activa')

            # Crear el diagnóstico
            diagnostico = Diagnostico.objects.create(
                key='movilidad_dental',
                categoria=categoria,
                nombre='Movilidad Dental',
                siglas='MD',
                simbolo_color='#FF0000',
                prioridad=3,  # Base, se ajusta según grado
                activo=True,
                codigo_icd10='K03.1',  # Aumento de movilidad dentaria
                codigo_cdt='D0460',  # Evaluación pulpar
                codigo_fhir='109564002',  # SNOMED CT: Tooth mobility
                tipo_recurso_fhir='Observation',
                simbolo_formulario_033='',
                superficie_aplicables=[]  # Afecta al diente completo
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Diagnóstico "{diagnostico.nombre}" creado exitosamente'
                )
            )

            # Asociar con el atributo de movilidad dental
            try:
                atributo = TipoAtributoClinico.objects.get(key='movilidad_dental')

                DiagnosticoAtributoClinico.objects.create(
                    diagnostico=diagnostico,
                    tipo_atributo=atributo
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Atributo "{atributo.nombre}" asociado al diagnóstico'
                    )
                )

                # Mostrar opciones disponibles
                opciones_count = atributo.opciones.count()
                self.stdout.write(
                    f'\n📋 {opciones_count} opciones de movilidad disponibles:'
                )
                for opcion in atributo.opciones.all().order_by('orden'):
                    self.stdout.write(
                        f'  • {opcion.nombre} - Prioridad {opcion.prioridad}'
                    )

            except TipoAtributoClinico.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️  El atributo "movilidad_dental" no existe. '
                        'Ejecuta primero: python manage.py agregar_movilidad_dental'
                    )
                )

            # Resumen
            self.stdout.write('\n📊 RESUMEN:')
            self.stdout.write(f'  • Categoría: {diagnostico.categoria.nombre}')
            self.stdout.write(f'  • Siglas: {diagnostico.siglas}')
            self.stdout.write(f'  • Prioridad base: {diagnostico.prioridad}')
            self.stdout.write(f'  • Código ICD-10: {diagnostico.codigo_icd10}')
            self.stdout.write(f'  • Código SNOMED: {diagnostico.codigo_fhir}')

            self.stdout.write('\n💡 FUNCIONAMIENTO:')
            self.stdout.write('  La prioridad efectiva se ajusta automáticamente según el grado:')
            self.stdout.write('  - Grado 0 → Prioridad 1 (informativa)')
            self.stdout.write('  - Grado 1 → Prioridad 2 (baja)')
            self.stdout.write('  - Grado 2 → Prioridad 4 (media-alta)')
            self.stdout.write('  - Grado 3 → Prioridad 5 (crítica)')

        except CategoriaDiagnostico.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    '❌ La categoría "patologia_activa" no existe en la base de datos'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al crear el diagnóstico: {str(e)}')
            )