# api/odontogram/management/commands/cargar_odontograma_csv.py
import csv
import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction

from api.odontogram.models import (
    AreaAfectada,
    CategoriaDiagnostico,
    Diagnostico,
    TipoAtributoClinico,
    OpcionAtributoClinico,
    DiagnosticoAreaAfectada,
    DiagnosticoAtributoClinico,
)


class Command(BaseCommand):
    help = 'Carga datos del odontograma desde archivos CSV alineados al Formulario 033'

    def __init__(self):
        super().__init__()
        # Ruta a la carpeta de datos CSV
        self.data_dir = Path(__file__).resolve().parent.parent.parent / 'data'
        self.stats = {
            'areas': 0,
            'tipos_atributos': 0,
            'opciones_atributos': 0,
            'categorias': 0,
            'diagnosticos': 0,
            'diagnostico_areas': 0,
            'diagnostico_atributos': 0,
        }

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpia los datos existentes antes de cargar',
        )
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Solo valida los CSV sin cargar datos',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('   CARGA DE DATOS DEL ODONTOGRAMA - FORMULARIO 033'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        try:
            # Verificar que exista la carpeta de datos
            if not self.data_dir.exists():
                self.stdout.write(self.style.ERROR(
                    f'❌ Carpeta {self.data_dir} no existe\n'
                    f'   Créala con: mkdir -p {self.data_dir}'
                ))
                return

            # Validar archivos CSV
            if not self._validate_csv_files():
                return

            # Solo validar si se solicita
            if options['validate']:
                self.stdout.write(self.style.SUCCESS('\n✓ Validación completada\n'))
                return

            # Limpiar datos si se solicita
            if options['clear']:
                if not self._confirm_clear():
                    self.stdout.write(self.style.WARNING('Operación cancelada'))
                    return
                self._clear_data()

            # Cargar datos en orden correcto
            with transaction.atomic():
                self._load_areas()
                self._load_tipos_atributos()
                self._load_opciones_atributos()
                self._load_categorias()
                self._load_diagnosticos()
                self._load_diagnostico_areas()
                self._load_diagnostico_atributos()

            # Mostrar resumen
            self._print_summary()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error: {str(e)}\n'))
            import traceback
            traceback.print_exc()
            raise

    def _confirm_clear(self):
        """Confirma que el usuario quiere limpiar los datos"""
        self.stdout.write(self.style.WARNING(
            '\n⚠️  ADVERTENCIA: Se eliminarán TODOS los datos del catálogo de odontograma'
        ))
        response = input('¿Estás seguro? Escribe "SI" para confirmar: ')
        return response.strip().upper() == 'SI'

    def _validate_csv_files(self):
        """Valida que existan todos los archivos CSV necesarios"""
        required_files = [
            'areas_afectadas.csv',
            'tipos_atributos.csv',
            'opciones_atributos.csv',
            'categorias_diagnostico.csv',
            'diagnosticos.csv',
            'diagnostico_areas.csv',
            'diagnostico_atributos.csv',
        ]

        self.stdout.write('Validando archivos CSV...\n')
        missing_files = []

        for filename in required_files:
            filepath = self.data_dir / filename
            if filepath.exists():
                size = filepath.stat().st_size
                self.stdout.write(f'  ✓ {filename} ({size} bytes)')
            else:
                self.stdout.write(self.style.ERROR(f'  ❌ {filename} (no encontrado)'))
                missing_files.append(filename)

        if missing_files:
            self.stdout.write(self.style.ERROR(
                f'\n❌ Faltan {len(missing_files)} archivo(s)\n'
            ))
            return False

        self.stdout.write(self.style.SUCCESS('\n✓ Todos los archivos encontrados\n'))
        return True

    def _clear_data(self):
        """Limpia todos los datos del odontograma"""
        self.stdout.write(self.style.WARNING('\nLimpiando datos existentes...'))
        
        counts = {
            'Relaciones Diagnóstico-Área': DiagnosticoAreaAfectada.objects.all().delete()[0],
            'Relaciones Diagnóstico-Atributo': DiagnosticoAtributoClinico.objects.all().delete()[0],
            'Diagnósticos': Diagnostico.objects.all().delete()[0],
            'Categorías': CategoriaDiagnostico.objects.all().delete()[0],
            'Opciones Atributos': OpcionAtributoClinico.objects.all().delete()[0],
            'Tipos Atributos': TipoAtributoClinico.objects.all().delete()[0],
            'Áreas Afectadas': AreaAfectada.objects.all().delete()[0],
        }
        
        for nombre, count in counts.items():
            if count > 0:
                self.stdout.write(f'  ✓ {nombre}: {count} eliminados')

    def _load_csv(self, filename):
        """Carga un archivo CSV y retorna una lista de diccionarios"""
        filepath = self.data_dir / filename

        if not filepath.exists():
            self.stdout.write(self.style.WARNING(f'⚠️  Archivo no encontrado: {filename}'))
            return []

        rows = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        return rows

    def _parse_bool(self, value):
        """Convierte cadena a booleano"""
        if value is None or value == '':
            return True
        return str(value).lower() in ('true', '1', 'yes', 'on', 'si', 'sí')

    def _parse_int(self, value):
        """Convierte cadena a entero, retorna None si está vacío"""
        if not value or str(value).strip() == '':
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _parse_json(self, value):
        """Convierte cadena JSON a objeto Python"""
        if not value or str(value).strip() == '':
            return []
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            self.stdout.write(self.style.WARNING(f'⚠️  JSON inválido: {value}'))
            return []

    def _load_areas(self):
        """Carga áreas afectadas desde CSV"""
        self.stdout.write(self.style.SUCCESS('\n1. Cargando Áreas Afectadas...'))
        rows = self._load_csv('areas_afectadas.csv')

        for row in rows:
            area, created = AreaAfectada.objects.get_or_create(
                key=row['key'],
                defaults={
                    'nombre': row['nombre'],
                    'activo': self._parse_bool(row.get('activo', 'True')),
                }
            )
            if created:
                self.stats['areas'] += 1
                self.stdout.write(f'  ✓ {area.nombre}')
            else:
                self.stdout.write(f'  → {area.nombre} (ya existe)')

    def _load_tipos_atributos(self):
        """Carga tipos de atributos clínicos desde CSV"""
        self.stdout.write(self.style.SUCCESS('\n2. Cargando Tipos de Atributos Clínicos...'))
        rows = self._load_csv('tipos_atributos.csv')

        for row in rows:
            tipo, created = TipoAtributoClinico.objects.get_or_create(
                key=row['key'],
                defaults={
                    'nombre': row['nombre'],
                    'descripcion': row.get('descripcion', ''),
                    'activo': self._parse_bool(row.get('activo', 'True')),
                }
            )
            if created:
                self.stats['tipos_atributos'] += 1
                self.stdout.write(f'  ✓ {tipo.nombre}')
            else:
                self.stdout.write(f'  → {tipo.nombre} (ya existe)')

    def _load_opciones_atributos(self):
        """Carga opciones de atributos desde CSV"""
        self.stdout.write(self.style.SUCCESS('\n3. Cargando Opciones de Atributos...'))
        rows = self._load_csv('opciones_atributos.csv')

        for row in rows:
            try:
                tipo = TipoAtributoClinico.objects.get(key=row['tipo_atributo_key'])

                opcion, created = OpcionAtributoClinico.objects.get_or_create(
                    tipo_atributo=tipo,
                    key=row['key'],
                    defaults={
                        'nombre': row['nombre'],
                        'prioridad': self._parse_int(row.get('prioridad')),
                        'orden': int(row.get('orden', 0)),
                        'activo': self._parse_bool(row.get('activo', 'True')),
                    }
                )
                if created:
                    self.stats['opciones_atributos'] += 1
                    self.stdout.write(f'  ✓ {tipo.nombre}: {opcion.nombre}')

            except TipoAtributoClinico.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  Tipo de atributo no encontrado: {row["tipo_atributo_key"]}'
                ))

    def _load_categorias(self):
        """Carga categorías de diagnóstico desde CSV"""
        self.stdout.write(self.style.SUCCESS('\n4. Cargando Categorías de Diagnóstico...'))
        rows = self._load_csv('categorias_diagnostico.csv')

        for row in rows:
            categoria, created = CategoriaDiagnostico.objects.get_or_create(
                key=row['key'],
                defaults={
                    'nombre': row['nombre'],
                    'color_key': row['color_key'],
                    'prioridad_key': row['prioridad_key'],
                    'activo': self._parse_bool(row.get('activo', 'True')),
                }
            )
            if created:
                self.stats['categorias'] += 1
                self.stdout.write(f'  ✓ {categoria.nombre} ({categoria.color_key})')
            else:
                self.stdout.write(f'  → {categoria.nombre} (ya existe)')

    def _load_diagnosticos(self):
        """Carga diagnósticos desde CSV con campos extendidos del Formulario 033"""
        self.stdout.write(self.style.SUCCESS('\n5. Cargando Diagnósticos (Form 033)...'))
        rows = self._load_csv('diagnosticos.csv')

        for row in rows:
            try:
                categoria = CategoriaDiagnostico.objects.get(key=row['categoria_key'])

                # ✅ CAMPOS EXTENDIDOS PARA FORM 033
                defaults = {
                    'categoria': categoria,
                    'nombre': row['nombre'],
                    'siglas': row.get('siglas', ''),
                    'simbolo_color': row['simbolo_color'],
                    'prioridad': int(row['prioridad']),
                    'activo': self._parse_bool(row.get('activo', 'True')),
                }

                # Códigos estándar (opcionales)
                if row.get('codigo_icd10'):
                    defaults['codigo_icd10'] = row['codigo_icd10']
                if row.get('codigo_cdt'):
                    defaults['codigo_cdt'] = row['codigo_cdt']
                if row.get('codigo_fhir'):
                    defaults['codigo_fhir'] = row['codigo_fhir']
                
                # Tipo recurso FHIR (opcional)
                if row.get('tipo_recurso_fhir'):
                    defaults['tipo_recurso_fhir'] = row['tipo_recurso_fhir']
                
                # ✅ CRÍTICO: Símbolo Formulario 033
                if row.get('simbolo_formulario_033'):
                    defaults['simbolo_formulario_033'] = row['simbolo_formulario_033']
                
                # ✅ Superficies aplicables (JSON)
                if row.get('superficie_aplicables'):
                    defaults['superficie_aplicables'] = self._parse_json(
                        row['superficie_aplicables']
                    )

                diagnostico, created = Diagnostico.objects.get_or_create(
                    key=row['key'],
                    defaults=defaults
                )
                
                if created:
                    self.stats['diagnosticos'] += 1
                    simbolo = diagnostico.simbolo_formulario_033 or 'N/A'
                    self.stdout.write(
                        f'  ✓ {diagnostico.siglas}: {diagnostico.nombre} '
                        f'[{simbolo}]'
                    )
                else:
                    self.stdout.write(f'  → {diagnostico.nombre} (ya existe)')

            except CategoriaDiagnostico.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  Categoría no encontrada: {row["categoria_key"]}'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'  ❌ Error en diagnóstico {row.get("key", "desconocido")}: {str(e)}'
                ))

    def _load_diagnostico_areas(self):
        """Carga relaciones diagnóstico-área desde CSV"""
        self.stdout.write(self.style.SUCCESS('\n6. Cargando Relaciones Diagnóstico-Área...'))
        rows = self._load_csv('diagnostico_areas.csv')

        for row in rows:
            try:
                diagnostico = Diagnostico.objects.get(key=row['diagnostico_key'])
                area = AreaAfectada.objects.get(key=row['area_key'])

                _, created = DiagnosticoAreaAfectada.objects.get_or_create(
                    diagnostico=diagnostico,
                    area=area
                )
                
                if created:
                    self.stats['diagnostico_areas'] += 1

            except Diagnostico.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  Diagnóstico no encontrado: {row["diagnostico_key"]}'
                ))
            except AreaAfectada.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  Área no encontrada: {row["area_key"]}'
                ))

        self.stdout.write(f'  ✓ {self.stats["diagnostico_areas"]} relaciones creadas')

    def _load_diagnostico_atributos(self):
        """Carga relaciones diagnóstico-atributo desde CSV"""
        self.stdout.write(self.style.SUCCESS('\n7. Cargando Relaciones Diagnóstico-Atributo...'))
        rows = self._load_csv('diagnostico_atributos.csv')

        for row in rows:
            try:
                diagnostico = Diagnostico.objects.get(key=row['diagnostico_key'])
                tipo_atributo = TipoAtributoClinico.objects.get(
                    key=row['tipo_atributo_key']
                )

                _, created = DiagnosticoAtributoClinico.objects.get_or_create(
                    diagnostico=diagnostico,
                    tipo_atributo=tipo_atributo
                )
                
                if created:
                    self.stats['diagnostico_atributos'] += 1

            except Diagnostico.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  Diagnóstico no encontrado: {row["diagnostico_key"]}'
                ))
            except TipoAtributoClinico.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  Tipo atributo no encontrado: {row["tipo_atributo_key"]}'
                ))

        self.stdout.write(f'  ✓ {self.stats["diagnostico_atributos"]} relaciones creadas')

    def _print_summary(self):
        """Imprime resumen de la carga"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('   RESUMEN DE CARGA'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        total = sum(self.stats.values())
        
        self.stdout.write(f'\n  Áreas Afectadas:              {self.stats["areas"]} creadas')
        self.stdout.write(f'  Tipos de Atributos:           {self.stats["tipos_atributos"]} creados')
        self.stdout.write(f'  Opciones de Atributos:        {self.stats["opciones_atributos"]} creadas')
        self.stdout.write(f'  Categorías de Diagnóstico:    {self.stats["categorias"]} creadas')
        self.stdout.write(f'  Diagnósticos:                 {self.stats["diagnosticos"]} creados')
        self.stdout.write(f'  Relaciones Diag-Área:         {self.stats["diagnostico_areas"]} creadas')
        self.stdout.write(f'  Relaciones Diag-Atributo:     {self.stats["diagnostico_atributos"]} creadas')
        
        self.stdout.write(self.style.SUCCESS(f'\n  TOTAL: {total} registros creados'))
        self.stdout.write(self.style.SUCCESS('\n' + '='*60 + '\n'))
        self.stdout.write(self.style.SUCCESS('  ✓ Carga completada exitosamente\n'))
