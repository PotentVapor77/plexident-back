# api/odontogram/management/commands/cargar_catalogo_odontologico.py
from django.core.management.base import BaseCommand
import csv
from io import StringIO
from api.odontogram.models import (
    CategoriaDiagnostico, Diagnostico, AreaAfectada, 
    DiagnosticoAreaAfectada, TipoAtributoClinico, 
    OpcionAtributoClinico, DiagnosticoAtributoClinico,
    DiagnosticoDental  # Necesario para limpiar datos dependientes
)

class Command(BaseCommand):
    help = 'Elimina TODOS los datos odontológicos y recarga catálogo desde CSV'

    def handle(self, *args, **options):
        self.stdout.write('🚨 ADVERTENCIA: Esto ELIMINARÁ TODOS los datos odontológicos!')
        confirm = input('¿Confirmar? (s/N): ')
        if confirm.lower() != 's':
            self.stdout.write('Cancelado.')
            return
            
        self.stdout.write('Iniciando limpieza completa...')
        
        # ORDEN CRÍTICO: Eliminar dependientes PRIMERO
        self.stdout.write('1. Eliminando DiagnosticoDental...')
        DiagnosticoDental.objects.all().delete()
        
        self.stdout.write('2. Eliminando relaciones M2M...')
        DiagnosticoAtributoClinico.objects.all().delete()
        DiagnosticoAreaAfectada.objects.all().delete()
        
        self.stdout.write('3. Eliminando catálogos base...')
        OpcionAtributoClinico.objects.all().delete()
        TipoAtributoClinico.objects.all().delete()
        AreaAfectada.objects.all().delete()
        Diagnostico.objects.all().delete()
        CategoriaDiagnostico.objects.all().delete()
        
        self.stdout.write('✅ Limpieza completada [file:8].')
        
        # Cargar en orden correcto (padres primero)
        self.cargar_categorias()
        self.cargar_diagnosticos()
        self.cargar_areas()
        self.cargar_relaciones_areas()
        self.cargar_tipos_atributos()
        self.cargar_opciones_atributos()
        self.cargar_relaciones_atributos()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Catálogo odontológico recargado exitosamente!')
        )
        self.stdout.write(
            f'📊 Resumen: {CategoriaDiagnostico.objects.count()} cat, '
            f'{Diagnostico.objects.count()} diag, '
            f'{AreaAfectada.objects.count()} áreas'
        )

    def cargar_categorias(self):
        """Carga categorias_diagnostico.csv [file:5]"""
        data = """key,nombre,colorkey,prioridadkey,activo
patologiaactiva,Patología Activa,#FF0000,ALTA,true
tratamientorealizado,Tratamiento Realizado,#0000FF,MEDIA,true
ausencia,Ausencia,#000000,INFORMATIVA,true
preventivo,Preventivo,#00AA00,BAJA,true"""
        reader = csv.DictReader(StringIO(data))
        for row in reader:
            CategoriaDiagnostico.objects.update_or_create(
                key=row['key'],
                defaults={
                    'nombre': row['nombre'],
                    'colorkey': row['colorkey'],
                    'prioridadkey': row['prioridadkey'],
                    'activo': row['activo'].lower() == 'true'
                }
            )
        self.stdout.write(f'✅ {CategoriaDiagnostico.objects.count()} categorías [file:5]')

    def cargar_diagnosticos(self):
        """Carga diagnosticos.csv [file:6]"""
        data = """key,categoriakey,nombre,siglas,simbolocolor,prioridad,activo,codigoicd10,codigocdt,codigofhir,tiporecursofhir,simboloformulario033,superficieaplicables
caries,patologiaactiva,Caries,C,,FF0000,5,true,K02.9,D0220,80967001,Condition,"O rojo","oclusal,vestibular,lingual,mesial,distal"
extraccionindicada,patologiaactiva,Extracción Indicada,Ext,,FF0000,5,true,Z48.0,D7140,385093006,Procedure,"X rojo",
sellantenecesario,patologiaactiva,Sellante Necesario,SN,,FF0000,3,true,D1351,67889009,Procedure,"U rojo",oclusal
sellanterealizado,tratamientorealizado,Sellante Realizado,SR,,0000FF,2,true,D1351,67889009,Procedure,"U azul",oclusal
endodonciaindicada,patologiaactiva,Endodoncia Por Realizar,Endo,,FF0000,5,true,D3310,234888008,Procedure,r,"raizmesial,raizdistal,raizpalatal,raizprincipal"
endodonciarealizda,tratamientorealizado,Endodoncia Realizada,ER,,0000FF,3,true,D3310,234888008,Procedure,azul,"raizmesial,raizdistal,raizpalatal,raizprincipal"
obturacion,tratamientorealizado,Obturado,Obt,,0000FF,2,true,Z98.891,D2391,28813003,Procedure,"o azul","oclusal,vestibular,lingual,mesial,distal"
ausente,ausencia,Ausente,A,,000000,1,true,K08.1,80967001,Condition,A,
protesisfijaindicada,patologiaactiva,Prótesis Fija Indicada,PFI,,FF0000,4,true,D6210,257281008,Procedure,--,
protesisfijarealizada,tratamientorealizado,Prótesis Fija Realizada,PFR,,0000FF,2,true,D6210,257281008,Procedure,"--azul",
coronaindicada,patologiaactiva,Corona Indicada,CI,,FF0000,4,true,D2740,309824003,Procedure,corona,
coronarealizada,tratamientorealizado,Corona Realizada,CR,,0000FF,2,true,D2740,309824003,Procedure,"azul corona",
dientessano,preventivo,Diente Sano,Sano,,00AA00,1,true,38199008,,Observation,check,"" """
        reader = csv.DictReader(StringIO(data))
        for row in reader:
            Diagnostico.objects.update_or_create(
                key=row['key'],
                defaults={
                    'categoria_id': row['categoriakey'],
                    'nombre': row['nombre'],
                    'siglas': row['siglas'],
                    'simbolocolor': row['simbolocolor'],
                    'prioridad': int(row['prioridad']),
                    'activo': row['activo'].lower() == 'true',
                    'codigoicd10': row['codigoicd10'],
                    'codigocdt': row['codigocdt'],
                    'codigofhir': row['codigofhir'],
                    'tiporecursofhir': row['tiporecursofhir'],
                    'simboloformulario033': row['simboloformulario033'],
                    'superficieaplicables': row['superficieaplicables']
                }
            )
        self.stdout.write(f'✅ {Diagnostico.objects.count()} diagnósticos [file:6]')

    def cargar_areas(self):
        """Carga areas_afectadas.csv [file:2]"""
        data = """key,nombre,activo
corona,Corona,true
raiz,Raíz,true
general,General,true"""
        reader = csv.DictReader(StringIO(data))
        for row in reader:
            AreaAfectada.objects.update_or_create(
                key=row['key'],
                defaults={'nombre': row['nombre'], 'activo': row['activo'].lower() == 'true'}
            )
        self.stdout.write(f'✅ {AreaAfectada.objects.count()} áreas [file:2]')

    def cargar_relaciones_areas(self):
        """Carga diagnostico_areas.csv [file:4]"""
        data = """diagnosticokey,areakey
caries,corona
obturacion,corona
endodonciarealizda,raiz
ausente,general"""
        reader = csv.DictReader(StringIO(data))
        count = 0
        for row in reader:
            diag, _ = Diagnostico.objects.get_or_create(key=row['diagnosticokey'])
            area, _ = AreaAfectada.objects.get_or_create(key=row['areakey'])
            DiagnosticoAreaAfectada.objects.get_or_create(
                diagnostico=diag, area=area
            )
            count += 1
        self.stdout.write(f'✅ {count} relaciones áreas [file:4]')

    def cargar_tipos_atributos(self):
        """Carga tipos_atributos.csv [file:7]"""
        data = """key,nombre,descripcion,activo
materialrestauracion,Material de Restauración,"Material utilizado en obturaciones/restauraciones",true
estadorestauracion,Estado de Restauración,"Condición actual de la restauración",true
localizacioncaries,Localización de Caries,"Profundidad o extensión de la caries",true
motivoextraccion,Motivo de Extracción,"Razón de la extracción dental",true
movilidaddental,Movilidad Dental,"Grado de movilidad del diente según escala de Miller",true"""
        reader = csv.DictReader(StringIO(data))
        for row in reader:
            TipoAtributoClinico.objects.update_or_create(
                key=row['key'],
                defaults={
                    'nombre': row['nombre'],
                    'descripcion': row['descripcion'],
                    'activo': row['activo'].lower() == 'true'
                }
            )
        self.stdout.write(f'✅ {TipoAtributoClinico.objects.count()} tipos atributos [file:7]')

    def cargar_opciones_atributos(self):
        """Carga opciones_atributos.csv [file:1]"""
        data = """tipoatributokey,key,nombre,prioridad,orden,activo
materialrestauracion,amalgama,Amalgama,1,1,true
materialrestauracion,resina,Resina Compuesta,2,2,true
materialrestauracion,ionomero,Ionomero de Vidrio,3,3,true
estadorestauracion,buena,Buena,1,1,true
estadorestauracion,aceptable,Aceptable,2,2,true"""
        reader = csv.DictReader(StringIO(data))
        count = 0
        for row in reader:
            tipo = TipoAtributoClinico.objects.get(key=row['tipoatributokey'])
            OpcionAtributoClinico.objects.update_or_create(
                tipoatributo=tipo, key=row['key'],
                defaults={
                    'nombre': row['nombre'],
                    'prioridad': int(row['prioridad']) if row['prioridad'] else None,
                    'orden': int(row['orden']) if row['orden'] else 0,
                    'activo': row['activo'].lower() == 'true'
                }
            )
            count += 1
        self.stdout.write(f'✅ {count} opciones atributos [file:1]')

    def cargar_relaciones_atributos(self):
        """Carga diagnostico_atributos.csv [file:3]"""
        data = """diagnosticokey,tipoatributokey
caries,localizacioncaries
obturacion,materialrestauracion
obturacion,estadorestauracion"""
        reader = csv.DictReader(StringIO(data))
        count = 0
        for row in reader:
            diag = Diagnostico.objects.get(key=row['diagnosticokey'])
            tipo = TipoAtributoClinico.objects.get(key=row['tipoatributokey'])
            DiagnosticoAtributoClinico.objects.get_or_create(
                diagnostico=diag, tipoatributo=tipo
            )
            count += 1
        self.stdout.write(f'✅ {count} relaciones atributos [file:3]')
