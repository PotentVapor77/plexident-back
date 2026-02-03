# api/odontogram/management/commands/limpiar_relaciones_atributos.py
# python manage.py limpiar_relaciones_atributos

from django.core.management.base import BaseCommand
from django.db import transaction

from api.odontogram.models import (
    Diagnostico,
    TipoAtributoClinico,
    DiagnosticoAtributoClinico,
)


class Command(BaseCommand):
    help = 'Elimina relaciones duplicadas o incorrectas entre diagnósticos y atributos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--diagnostico',
            type=str,
            help='Key del diagnóstico a limpiar (ej: perdida_otra_causa)',
        )
        parser.add_argument(
            '--tipo-atributo',
            type=str,
            help='Key del tipo de atributo a eliminar (ej: motivo_extraccion)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la eliminación sin aplicar cambios',
        )
        parser.add_argument(
            '--listar',
            action='store_true',
            help='Lista todas las relaciones existentes',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('   LIMPIEZA DE RELACIONES DIAGNÓSTICO-ATRIBUTO'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        # Listar todas las relaciones
        if options['listar']:
            self._listar_relaciones()
            return

        diagnostico_key = options.get('diagnostico')
        tipo_atributo_key = options.get('tipo_atributo')
        dry_run = options['dry_run']

        if not diagnostico_key or not tipo_atributo_key:
            self.stdout.write(self.style.ERROR(
                '❌ Debes especificar --diagnostico y --tipo-atributo\n'
                'Ejemplo: python manage.py limpiar_relaciones_atributos \\\n'
                '         --diagnostico perdida_otra_causa \\\n'
                '         --tipo-atributo motivo_extraccion\n'
            ))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODO SIMULACIÓN\n'))

        try:
            with transaction.atomic():
                diagnostico = Diagnostico.objects.get(key=diagnostico_key)
                tipo_atributo = TipoAtributoClinico.objects.get(key=tipo_atributo_key)

                # Buscar relación
                relacion = DiagnosticoAtributoClinico.objects.filter(
                    diagnostico=diagnostico,
                    tipo_atributo=tipo_atributo
                ).first()

                if relacion:
                    self.stdout.write(
                        f'🔍 Relación encontrada:\n'
                        f'   Diagnóstico: {diagnostico.nombre} ({diagnostico.key})\n'
                        f'   Atributo: {tipo_atributo.nombre} ({tipo_atributo.key})\n'
                    )

                    if not dry_run:
                        relacion.delete()
                        self.stdout.write(self.style.SUCCESS('\n✓ Relación eliminada exitosamente\n'))
                    else:
                        self.stdout.write(self.style.WARNING('\n⚠️  NO eliminado (--dry-run activo)\n'))
                        transaction.set_rollback(True)
                else:
                    self.stdout.write(self.style.WARNING(
                        f'⚠️  No se encontró relación entre:\n'
                        f'   {diagnostico_key} → {tipo_atributo_key}\n'
                    ))

        except Diagnostico.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Diagnóstico no encontrado: {diagnostico_key}'))
        except TipoAtributoClinico.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Tipo de atributo no encontrado: {tipo_atributo_key}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))

    def _listar_relaciones(self):
        """Lista todas las relaciones diagnóstico-atributo"""
        self.stdout.write('📋 RELACIONES ACTUALES:\n')
        
        relaciones = DiagnosticoAtributoClinico.objects.select_related(
            'diagnostico', 'tipo_atributo'
        ).order_by('diagnostico__key', 'tipo_atributo__key')

        diagnostico_actual = None
        for rel in relaciones:
            if diagnostico_actual != rel.diagnostico.key:
                diagnostico_actual = rel.diagnostico.key
                self.stdout.write(f'\n  {rel.diagnostico.nombre} ({rel.diagnostico.key}):')
            
            self.stdout.write(f'    → {rel.tipo_atributo.nombre} ({rel.tipo_atributo.key})')

        self.stdout.write(f'\n\n  Total: {relaciones.count()} relaciones\n')
