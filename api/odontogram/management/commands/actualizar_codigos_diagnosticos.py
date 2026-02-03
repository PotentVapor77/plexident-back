# api/odontogram/management/commands/actualizar_codigos_diagnosticos.py
# python manage.py actualizar_codigos_diagnosticos --verbose

import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction

from api.odontogram.models import Diagnostico


class Command(BaseCommand):
    help = 'Actualiza códigos ICD-10, CDT, FHIR y otros campos de diagnósticos existentes'

    def __init__(self):
        super().__init__()
        self.data_dir = Path(__file__).resolve().parent.parent.parent / 'data'
        self.stats = {
            'actualizados': 0,
            'sin_cambios': 0,
            'no_encontrados': 0,
            'errores': 0,
        }

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la actualización sin guardar cambios',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Muestra detalles de cada actualización',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('   ACTUALIZACIÓN DE CÓDIGOS DE DIAGNÓSTICOS'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        dry_run = options['dry_run']
        verbose = options['verbose']

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODO SIMULACIÓN (no se guardarán cambios)\n'))

        try:
            csv_path = self.data_dir / 'diagnosticos.csv'
            if not csv_path.exists():
                self.stdout.write(self.style.ERROR(f'❌ Archivo no encontrado: {csv_path}'))
                return

            rows = self._load_csv('diagnosticos.csv')
            
            if not rows:
                self.stdout.write(self.style.WARNING('⚠️  No se encontraron datos en el CSV'))
                return

            self.stdout.write(f'📋 Diagnósticos a procesar: {len(rows)}\n')

            # ✅ PROCESAMIENTO SIN BLOQUE ATÓMICO GLOBAL
            for row in rows:
                self._update_diagnostico(row, verbose, dry_run)

            self._print_summary()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error: {str(e)}\n'))
            import traceback
            traceback.print_exc()
            raise

    def _load_csv(self, filename):
        """Carga un archivo CSV y retorna una lista de diccionarios"""
        filepath = self.data_dir / filename
        rows = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        
        return rows

    def _parse_json(self, value):
        """Convierte cadena JSON a lista Python"""
        if not value or str(value).strip() == '':
            return []
        try:
            import json
            return json.loads(value)
        except json.JSONDecodeError:
            return []

    def _update_diagnostico(self, row, verbose, dry_run):
        """Actualiza un diagnóstico individual con transacción propia"""
        key = row['key']
        
        try:
            # ✅ Transacción individual por diagnóstico
            with transaction.atomic():
                diagnostico = Diagnostico.objects.get(key=key)
                
                updates = {}
                cambios = []

                # Campos básicos
                if row.get('nombre') and diagnostico.nombre != row['nombre']:
                    updates['nombre'] = row['nombre']
                    cambios.append(f"nombre: '{diagnostico.nombre}' → '{row['nombre']}'")

                if row.get('siglas') and diagnostico.siglas != row['siglas']:
                    updates['siglas'] = row['siglas']
                    cambios.append(f"siglas: '{diagnostico.siglas}' → '{row['siglas']}'")

                if row.get('simbolo_color') and diagnostico.simbolo_color != row['simbolo_color']:
                    updates['simbolo_color'] = row['simbolo_color']
                    cambios.append(f"color: '{diagnostico.simbolo_color}' → '{row['simbolo_color']}'")

                # ✅ CÓDIGOS ESTÁNDAR - SOLO ACTUALIZAR SI HAY VALOR EN CSV
                nuevo_icd10 = row.get('codigo_icd10', '').strip()
                if nuevo_icd10:  # Solo actualizar si hay valor
                    if diagnostico.codigo_icd10 != nuevo_icd10:
                        updates['codigo_icd10'] = nuevo_icd10
                        cambios.append(f"ICD-10: '{diagnostico.codigo_icd10 or 'NULL'}' → '{nuevo_icd10}'")

                nuevo_cdt = row.get('codigo_cdt', '').strip()
                if nuevo_cdt:  # Solo actualizar si hay valor
                    if diagnostico.codigo_cdt != nuevo_cdt:
                        updates['codigo_cdt'] = nuevo_cdt
                        cambios.append(f"CDT: '{diagnostico.codigo_cdt or 'NULL'}' → '{nuevo_cdt}'")

                nuevo_fhir = row.get('codigo_fhir', '').strip()
                if nuevo_fhir:  # Solo actualizar si hay valor
                    if diagnostico.codigo_fhir != nuevo_fhir:
                        updates['codigo_fhir'] = nuevo_fhir
                        cambios.append(f"FHIR: '{diagnostico.codigo_fhir or 'NULL'}' → '{nuevo_fhir}'")

                # Tipo recurso FHIR
                nuevo_tipo_fhir = row.get('tipo_recurso_fhir', '').strip()
                if nuevo_tipo_fhir:
                    if diagnostico.tipo_recurso_fhir != nuevo_tipo_fhir:
                        updates['tipo_recurso_fhir'] = nuevo_tipo_fhir
                        cambios.append(f"FHIR Resource: '{diagnostico.tipo_recurso_fhir or 'NULL'}' → '{nuevo_tipo_fhir}'")

                # Símbolo Formulario 033
                nuevo_simbolo = row.get('simbolo_formulario_033', '').strip()
                if nuevo_simbolo:
                    if diagnostico.simbolo_formulario_033 != nuevo_simbolo:
                        updates['simbolo_formulario_033'] = nuevo_simbolo
                        cambios.append(f"Símbolo 033: '{diagnostico.simbolo_formulario_033 or 'NULL'}' → '{nuevo_simbolo}'")

                # Superficies aplicables
                nuevas_superficies = self._parse_json(row.get('superficie_aplicables', '[]'))
                if nuevas_superficies != diagnostico.superficie_aplicables:
                    updates['superficie_aplicables'] = nuevas_superficies
                    cambios.append(f"Superficies: {diagnostico.superficie_aplicables} → {nuevas_superficies}")

                # Prioridad
                nueva_prioridad = int(row.get('prioridad', diagnostico.prioridad))
                if nueva_prioridad != diagnostico.prioridad:
                    updates['prioridad'] = nueva_prioridad
                    cambios.append(f"Prioridad: {diagnostico.prioridad} → {nueva_prioridad}")

                # Aplicar actualizaciones
                if updates:
                    for field, value in updates.items():
                        setattr(diagnostico, field, value)
                    
                    if not dry_run:
                        diagnostico.save(update_fields=list(updates.keys()))
                    
                    self.stats['actualizados'] += 1
                    
                    if verbose:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ {diagnostico.siglas}: {diagnostico.nombre}'))
                        for cambio in cambios:
                            self.stdout.write(f'    • {cambio}')
                    else:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ {diagnostico.siglas} ({len(cambios)} cambios)'))
                else:
                    self.stats['sin_cambios'] += 1
                    if verbose:
                        self.stdout.write(f'  → {diagnostico.siglas}: sin cambios')

                # Rollback si es dry-run
                if dry_run:
                    transaction.set_rollback(True)

        except Diagnostico.DoesNotExist:
            self.stats['no_encontrados'] += 1
            self.stdout.write(self.style.WARNING(f'  ⚠️  Diagnóstico no encontrado: {key}'))
        
        except Exception as e:
            self.stats['errores'] += 1
            self.stdout.write(self.style.ERROR(f'  ❌ Error en {key}: {str(e)}'))

    def _print_summary(self):
        """Imprime resumen de la actualización"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('   RESUMEN DE ACTUALIZACIÓN'))
        self.stdout.write(self.style.SUCCESS('='*70))
        
        total_procesados = sum(self.stats.values())
        
        self.stdout.write(f'\n  ✓ Actualizados:       {self.stats["actualizados"]}')
        self.stdout.write(f'  → Sin cambios:        {self.stats["sin_cambios"]}')
        
        if self.stats['no_encontrados'] > 0:
            self.stdout.write(self.style.WARNING(f'  ⚠️  No encontrados:    {self.stats["no_encontrados"]}'))
        
        if self.stats['errores'] > 0:
            self.stdout.write(self.style.ERROR(f'  ❌ Errores:           {self.stats["errores"]}'))
        
        self.stdout.write(f'\n  Total procesados:    {total_procesados}')
        self.stdout.write(self.style.SUCCESS('\n' + '='*70 + '\n'))
