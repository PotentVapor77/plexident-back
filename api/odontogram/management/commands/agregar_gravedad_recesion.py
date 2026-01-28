# api/odontogram/management/commands/agregar_gravedad_recesion.py
"""
Comando Django para agregar el diagnóstico de Recesión Gingival con atributo de gravedad
Uso: python manage.py agregar_gravedad_recesion
"""

from django.core.management.base import BaseCommand
from api.odontogram.models import (
    Diagnostico, 
    CategoriaDiagnostico, 
    TipoAtributoClinico,
    OpcionAtributoClinico,
    DiagnosticoAtributoClinico,
    DiagnosticoAreaAfectada,
    AreaAfectada
)


class Command(BaseCommand):
    help = 'Agrega el diagnóstico de Recesión Gingival con atributo de gravedad'

    def handle(self, *args, **options):
        self.stdout.write('🔍 Verificando y configurando diagnóstico de Recesión Gingival...')
        
        # 1. Verificar si el diagnóstico ya existe
        if Diagnostico.objects.filter(key='recesion_gingival').exists():
            self.stdout.write(
                self.style.WARNING('⚠️  El diagnóstico "recesion_gingival" ya existe')
            )
            # Verificar si ya tiene el atributo asociado
            diagnostico = Diagnostico.objects.get(key='recesion_gingival')
            try:
                atributo = TipoAtributoClinico.objects.get(key='gravedad_recesion')
                if DiagnosticoAtributoClinico.objects.filter(
                    diagnostico=diagnostico, 
                    tipo_atributo=atributo
                ).exists():
                    self.stdout.write(
                        self.style.WARNING('⚠️  El atributo ya está asociado al diagnóstico')
                    )
                    return
            except TipoAtributoClinico.DoesNotExist:
                pass
        
        try:
            # 2. Obtener la categoría Patología Activa
            categoria = CategoriaDiagnostico.objects.get(key='patologia_activa')
            
            # 3. Crear o actualizar el diagnóstico - CORREGIDO CON NOMBRES DE CAMPO CORRECTOS
            diagnostico, created = Diagnostico.objects.update_or_create(
                key='recesion_gingival',
                defaults={
                    'categoria': categoria,
                    'nombre': 'Recesión Gingival',
                    'siglas': 'RG',
                    'simbolo_color': '#EAB308',  # Color amarillo/naranja
                    'prioridad': 2,  # Prioridad base
                    'activo': True,
                    'codigo_icd10': 'K06.0',  # Recesión gingival
                    'codigo_cdt': 'D4341',  # Escalamiento y alisado radicular por cuadrante
                    'codigo_fhir': '109983006',  # SNOMED CT: Gingival recession
                    'tipo_recurso_fhir': 'Observation',
                    'simbolo_formulario_033': '',
                    'superficie_aplicables': '[]'  # Array vacío como string JSON
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Diagnóstico "{diagnostico.nombre}" creado exitosamente')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Diagnóstico "{diagnostico.nombre}" actualizado')
                )
            
            # 4. Asociar con área afectada "general"
            try:
                area_general = AreaAfectada.objects.get(key='general')
                DiagnosticoAreaAfectada.objects.get_or_create(
                    diagnostico=diagnostico,
                    area=area_general
                )
                self.stdout.write(
                    self.style.SUCCESS('✅ Área "General" asociada al diagnóstico')
                )
            except AreaAfectada.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING('⚠️  Área "general" no encontrada')
                )
            
            # 5. Verificar o crear el atributo de gravedad
            try:
                atributo = TipoAtributoClinico.objects.get(key='gravedad_recesion')
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Atributo "{atributo.nombre}" encontrado')
                )
            except TipoAtributoClinico.DoesNotExist:
                # Crear el atributo si no existe
                atributo = TipoAtributoClinico.objects.create(
                    key='gravedad_recesion',
                    nombre='Gravedad de Recesión',
                    descripcion='Gravedad de la recesión gingival',
                    activo=True
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Atributo "{atributo.nombre}" creado')
                )
            
            # 6. Crear opciones de gravedad si no existen
            opciones_data = [
                {'key': 'leve', 'nombre': 'Leve (1-2mm)', 'prioridad': 1, 'orden': 1},
                {'key': 'moderada', 'nombre': 'Moderada (3-4mm)', 'prioridad': 2, 'orden': 2},
                {'key': 'severa', 'nombre': 'Severa (5mm o más)', 'prioridad': 3, 'orden': 3}
            ]
            
            for opcion_data in opciones_data:
                opcion, created_opcion = OpcionAtributoClinico.objects.update_or_create(
                    tipo_atributo=atributo,
                    key=opcion_data['key'],
                    defaults={
                        'nombre': opcion_data['nombre'],
                        'prioridad': opcion_data['prioridad'],
                        'orden': opcion_data['orden'],
                        'activo': True
                    }
                )
                if created_opcion:
                    self.stdout.write(f'  • Opción "{opcion.nombre}" creada')
                else:
                    self.stdout.write(f'  • Opción "{opcion.nombre}" actualizada')
            
            # 7. Asociar diagnóstico con atributo
            relacion, created_rel = DiagnosticoAtributoClinico.objects.get_or_create(
                diagnostico=diagnostico,
                tipo_atributo=atributo
            )
            
            if created_rel:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Atributo "{atributo.nombre}" asociado al diagnóstico')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Relación ya existente actualizada')
                )
            
            # 8. Mostrar resumen
            self.stdout.write('\n📊 RESUMEN DEL DIAGNÓSTICO:')
            self.stdout.write(f'  • Nombre: {diagnostico.nombre}')
            self.stdout.write(f'  • Siglas: {diagnostico.siglas}')
            self.stdout.write(f'  • Categoría: {diagnostico.categoria.nombre}')
            self.stdout.write(f'  • Prioridad: {diagnostico.prioridad}')
            self.stdout.write(f'  • Código ICD-10: {diagnostico.codigo_icd10}')
            self.stdout.write(f'  • Código SNOMED: {diagnostico.codigo_fhir}')
            
            self.stdout.write('\n📋 OPCIONES DE GRAVEDAD:')
            opciones = atributo.opciones.all().order_by('orden')
            for opcion in opciones:
                self.stdout.write(f'  • {opcion.nombre} (Prioridad: {opcion.prioridad})')
            
            self.stdout.write(
                self.style.SUCCESS('\n✅ Recesión Gingival configurada completamente!')
            )
            
        except CategoriaDiagnostico.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('❌ La categoría "patologia_activa" no existe')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {str(e)}')
            )