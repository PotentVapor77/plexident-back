import csv
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from api.odontogram.models import Diagnostico, CategoriaDiagnostico

class Command(BaseCommand):
    help = 'Actualiza los diagnósticos existentes desde el CSV sin borrar registros'

    def handle(self, *args, **options):
        # Ruta al archivo CSV (ajustada según la estructura de tus archivos)
        csv_path = Path(__file__).resolve().parent.parent.parent / 'data' / 'diagnosticos.csv'
        
        if not csv_path.exists():
            self.stdout.write(self.style.ERROR(f'No se encontró el archivo en: {csv_path}'))
            return

        self.stdout.write(self.style.SUCCESS('--- Iniciando Actualización de Diagnósticos ---'))
        
        actualizados = 0
        creados = 0
        errores = 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Usamos una transacción atómica para asegurar consistencia
            with transaction.atomic():
                for row in reader:
                    try:
                        # 1. Obtener la categoría (debe existir previamente) 
                        categoria = CategoriaDiagnostico.objects.get(key=row['categoria_key'])

                        # 2. Preparar los datos a actualizar
                        valores_update = {
                            'categoria': categoria,
                            'nombre': row['nombre'],
                            'siglas': row.get('siglas', ''),
                            'simbolo_color': row['simbolo_color'],
                            'prioridad': int(row['prioridad']),
                            'activo': row.get('activo', 'True').lower() in ('true', '1', 'si'),
                            'codigo_icd10': row.get('codigo_icd10'),
                            'codigo_cdt': row.get('codigo_cdt'),
                            'codigo_fhir': row.get('codigo_fhir'),
                            'tipo_recurso_fhir': row.get('tipo_recurso_fhir'),
                            'simbolo_formulario_033': row.get('simbolo_formulario_033'),
                        }

                        # Procesar superficies aplicables (JSON) 
                        superficies = row.get('superficie_aplicables', '[]')
                        try:
                            valores_update['superficie_aplicables'] = json.loads(superficies)
                        except json.JSONDecodeError:
                            # Si no es JSON válido, intentar parsear como lista simple si viene separado por comas
                            valores_update['superficie_aplicables'] = [s.strip() for s in superficies.split(',')] if superficies else []

                        # 3. Actualizar o Crear 
                        obj, created = Diagnostico.objects.update_or_create(
                            key=row['key'], # Clave de búsqueda
                            defaults=valores_update # Campos a actualizar
                        )

                        if created:
                            creados += 1
                            self.stdout.write(f"  + Creado: {obj.key}")
                        else:
                            actualizados += 1
                            self.stdout.write(f"  ~ Actualizado: {obj.key}")

                    except CategoriaDiagnostico.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"  ! Error: Categoría '{row['categoria_key']}' no existe para el diagnóstico {row['key']}"))
                        errores += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  ! Error en {row.get('key')}: {str(e)}"))
                        errores += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nResumen: {actualizados} actualizados, {creados} creados, {errores} errores.'
        ))