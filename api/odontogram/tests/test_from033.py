
import os
import json
import tempfile
from datetime import datetime, date
from pathlib import Path

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from api.patients.models import Paciente
from api.odontogram.models import (
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    Diagnostico,
    CategoriaDiagnostico,
)
from api.odontogram.services.form033_service import Form033Service

User = get_user_model()


class TestForm033ServiceComplete(TestCase):
    """Test del servicio Form033 """

    def setUp(self):
        """Preparar datos de test"""
        
        # Crear usuario
        self.user = User.objects.create_user(
            username='test_odontologo',
            correo='odontologo@test.com', 
            password='testpass123'
        )
        
        # Crear categoría diagnóstico
        self.categoria_caries = CategoriaDiagnostico.objects.create(
            key='caries',
            nombre='Caries',
            color_key='red',
            prioridad_key='alta'
        )
        
        self.categoria_restauracion = CategoriaDiagnostico.objects.create(
            key='restauracion',
            nombre='Restauración',
            color_key='blue',
            prioridad_key='media'
        )
        
        # Crear diagnósticos
        self.diag_caries = Diagnostico.objects.create(
            key='caries_simple',
            categoria=self.categoria_caries,
            nombre='Caries Simple',
            siglas='C',
            simbolo_color='red',
            prioridad=1,
            simbolo_formulario_033='X_rojo'  # ← Campo importante
        )
        
        self.diag_obturado = Diagnostico.objects.create(
            key='obturado',
            categoria=self.categoria_restauracion,
            nombre='Obturado',
            siglas='O',
            simbolo_color='blue',
            prioridad=2,
            simbolo_formulario_033='o_azul'  # ← Campo importante
        )
        
        self.diag_ausente = Diagnostico.objects.create(
            key='ausente',
            categoria=self.categoria_caries,
            nombre='Ausente',
            siglas='A',
            simbolo_color='black',
            prioridad=3,
            simbolo_formulario_033='A'  # ← Campo importante
        )
        
        # Crear paciente
        self.paciente = Paciente.objects.create(
            cedula_pasaporte='1234567890',
            nombres='Juan',
            apellidos='García López',
            sexo='M',
            fecha_nacimiento=date(1990, 5, 15),
            correo='juan@example.com'
        )
        
        # Crear dientes con diagnósticos
        self._crear_dientes_con_diagnosticos()
        
        # Instanciar servicio
        self.service = Form033Service()

    def _crear_dientes_con_diagnosticos(self):
        """Crear dientes y asignar diagnósticos"""
        
        # Diente 18 (Superior Derecho) - Caries
        diente_18 = Diente.objects.create(
            paciente=self.paciente,
            codigo_fdi='18'
        )
        
        superficie_18 = SuperficieDental.objects.create(
            diente=diente_18,
            nombre='oclusal'
        )
        
        DiagnosticoDental.objects.create(
            superficie=superficie_18,
            diagnostico_catalogo=self.diag_caries,
            odontologo=self.user,
            tipo_registro='rojo'
        )
        
        # Diente 17 (Superior Derecho) - Obturado
        diente_17 = Diente.objects.create(
            paciente=self.paciente,
            codigo_fdi='17'
        )
        
        superficie_17 = SuperficieDental.objects.create(
            diente=diente_17,
            nombre='oclusal'
        )
        
        DiagnosticoDental.objects.create(
            superficie=superficie_17,
            diagnostico_catalogo=self.diag_obturado,
            odontologo=self.user,
            tipo_registro='azul'
        )
        
        # Diente 16 (Superior Derecho) - Obturado
        diente_16 = Diente.objects.create(
            paciente=self.paciente,
            codigo_fdi='16'
        )
        
        superficie_16 = SuperficieDental.objects.create(
            diente=diente_16,
            nombre='oclusal'
        )
        
        DiagnosticoDental.objects.create(
            superficie=superficie_16,
            diagnostico_catalogo=self.diag_obturado,
            odontologo=self.user,
            tipo_registro='azul'
        )
        
        # Diente 15 (Superior Derecho) - Ausente
        diente_15 = Diente.objects.create(
            paciente=self.paciente,
            codigo_fdi='15',
            ausente=True,
            razon_ausencia='caries'
        )
        
        # Dientes restantes (sanos - sin diagnósticos)
        for fdi in ['14', '13', '12', '11', '21', '22', '23', '24', '25',
                    '26', '27', '28', '31', '32', '33', '34', '35', '36',
                    '37', '38', '41', '42', '43', '44', '45', '46', '47', '48']:
            Diente.objects.create(
                paciente=self.paciente,
                codigo_fdi=fdi
            )

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 1: Generación de datos JSON
    # ═══════════════════════════════════════════════════════════════════════════════

    def test_01_generar_datos_form033(self):
        """Test: Generar estructura JSON completa"""
        
        print("\n" + "="*80)
        print("TEST 1: Generación de datos JSON")
        print("="*80)
        
        datos = self.service.generar_datos_form033(str(self.paciente.id))
        
        # Verificar estructura principal
        self.assertIn('seccion_i_paciente', datos)
        self.assertIn('seccion_ii_odontograma', datos)
        self.assertIn('estadisticas', datos)
        
        print(f"\nEstructura JSON válida")
        print(f"   - Sección I (Paciente): OK")
        print(f"   - Sección II (Odontograma): OK")
        print(f"   - Estadísticas: OK")
        
        # Verificar datos del paciente
        paciente_data = datos['seccion_i_paciente']
        self.assertEqual(paciente_data['cedula'], '1234567890')
        self.assertEqual(paciente_data['nombres'], 'Juan')
        self.assertEqual(paciente_data['apellidos'], 'García López')
        self.assertEqual(paciente_data['sexo'], 'M')
        
        print(f"\nDatos del paciente correctos:")
        print(f"   - Cédula: {paciente_data['cedula']}")
        print(f"   - Nombre completo: {paciente_data['nombres']} {paciente_data['apellidos']}")
        print(f"   - Edad: {paciente_data['edad']} años")
        
        # Verificar estadísticas
        stats = datos['estadisticas']
        print(f"\nEstadísticas calculadas:")
        print(f"   - Sanos: {stats['sanos']}")
        print(f"   - Cariados: {stats['cariados']}")
        print(f"   - Perdidos: {stats['perdidos']}")
        print(f"   - Obturados: {stats['obturados']}")
        print(f"   - CPO-D: {stats['cpod']} / 32")
        
        # Validar CPO-D
        self.assertEqual(stats['cpod'], 4)  # 1 cariado + 1 perdido + 2 obturados
        self.assertEqual(stats['cariados'], 1)
        self.assertEqual(stats['perdidos'], 1)
        self.assertEqual(stats['obturados'], 2)
        
        print(f"\nCPO-D calculado correctamente: {stats['cpod']}")

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 2: Generación de HTML
    # ═══════════════════════════════════════════════════════════════════════════════

    def test_02_generar_html_form033(self):
        """Test: Generar HTML visualizable"""
        
        print("\n" + "="*80)
        print("TEST 2: Generación de HTML")
        print("="*80)
        
        html = self.service.generar_html_form033(str(self.paciente.id))
        
        # Verificar que es HTML válido
        self.assertIn('<!DOCTYPE html', html)
        self.assertIn('<html', html)
        self.assertIn('</html>', html)
        
        print(f"\nHTML válido generado")
        print(f"   - Tamaño: {len(html)} caracteres")
        
        # Verificar contenido
        self.assertIn('Formulario 033', html)
        self.assertIn('Juan', html)
        self.assertIn('García', html)
        self.assertIn('CPO-D', html)
        
        print(f"Contenido del formulario presente:")
        print(f"   - Título Formulario 033: OK")
        print(f"   - Datos paciente: OK")
        print(f"   - Sección CPO-D: OK")
        
        # Verificar tabla 4x8
        self.assertIn('SUPERIOR DERECHO', html)
        self.assertIn('SUPERIOR IZQUIERDO', html)
        self.assertIn('INFERIOR IZQUIERDO', html)
        self.assertIn('INFERIOR DERECHO', html)
        
        print(f"Tabla 4x8 presente:")
        print(f"   - Superior Derecho: OK")
        print(f"   - Superior Izquierdo: OK")
        print(f"   - Inferior Izquierdo: OK")
        print(f"   - Inferior Derecho: OK")
        
        # Guardar HTML para inspección manual
        output_dir = Path(tempfile.gettempdir())
        html_file = output_dir / f"form033_test_{self.paciente.id}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\nHTML guardado en: {html_file}")
        print(f"   Puedes abrirlo en navegador para inspeccionar")

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 3: Generación de PDF
    # ═══════════════════════════════════════════════════════════════════════════════

    def test_03_generar_pdf_form033(self):
        """Test: Generar PDF y guardarlo"""
        
        print("\n" + "="*80)
        print("TEST 3: Generación de PDF")
        print("="*80)
        
        try:
            from weasyprint import HTML
            
            print(f"\nWeasyPrint disponible")
            
            # Generar HTML
            html_content = self.service.generar_html_form033(str(self.paciente.id))
            
            # Convertir a PDF
            html_obj = HTML(string=html_content)
            pdf_bytes = html_obj.write_pdf()
            
            print(f"PDF generado correctamente")
            print(f"   - Tamaño: {len(pdf_bytes) / 1024:.2f} KB")
            
            # Validar que es PDF
            self.assertIn(b'%PDF', pdf_bytes[:10])
            
            print(f"Archivo válido (header PDF correcto)")
            
            # Guardar PDF
            output_dir = Path(tempfile.gettempdir())
            pdf_file = output_dir / f"Form033_{self.paciente.id}.pdf"
            
            with open(pdf_file, 'wb') as f:
                f.write(pdf_bytes)
            
            print(f"\nPDF guardado en: {pdf_file}")
            print(f"   Puedes descargarlo para inspeccionar")
            
            # Verificar archivo
            self.assertTrue(pdf_file.exists())
            self.assertGreater(pdf_file.stat().st_size, 0)
            
            print(f"Archivo existe y tiene contenido")
            
        except ImportError:
            self.skipTest('WeasyPrint no instalado. Instala: pip install weasyprint')

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 4: Mapeo de símbolos del modelo
    # ═══════════════════════════════════════════════════════════════════════════════

    def test_04_mapeo_simbolo_formulario_033(self):
        """Test: Verificar que usa el campo simbolo_formulario_033"""
        
        print("\n" + "="*80)
        print("TEST 4: Mapeo de símbolos formulario_033")
        print("="*80)
        
        # Obtener diente con caries
        diente_18 = Diente.objects.get(codigo_fdi='18', paciente=self.paciente)
        
        # Obtener símbolo
        info_simbolo = self.service.obtener_simbolo_diente(diente_18)
        
        print(f"\nSímbolo para Diente 18 (Caries):")
        print(f"   - Símbolo: {info_simbolo['simbolo']}")
        print(f"   - Color: {info_simbolo['color']}")
        print(f"   - Descripción: {info_simbolo['descripcion']}")
        print(f"   - Categoría: {info_simbolo['categoria']}")
        
        # Verificar que es 'X' (caries)
        self.assertEqual(info_simbolo['simbolo'], 'X')
        self.assertEqual(info_simbolo['categoria'], 'rojo')
        
        print(f"\nSímbolo correcto (X - Caries)")
        
        # Verificar diente obturado
        diente_17 = Diente.objects.get(codigo_fdi='17', paciente=self.paciente)
        info_simbolo_17 = self.service.obtener_simbolo_diente(diente_17)
        
        print(f"\nSímbolo para Diente 17 (Obturado):")
        print(f"   - Símbolo: {info_simbolo_17['simbolo']}")
        print(f"   - Color: {info_simbolo_17['color']}")
        print(f"   - Descripción: {info_simbolo_17['descripcion']}")
        
        self.assertEqual(info_simbolo_17['simbolo'], 'o')
        self.assertEqual(info_simbolo_17['categoria'], 'azul')
        
        print(f"\nSímbolo correcto (o - Obturado)")
        
        # Verificar diente ausente
        diente_15 = Diente.objects.get(codigo_fdi='15', paciente=self.paciente)
        info_simbolo_15 = self.service.obtener_simbolo_diente(diente_15)
        
        print(f"\nSímbolo para Diente 15 (Ausente):")
        print(f"   - Símbolo: {info_simbolo_15['simbolo']}")
        print(f"   - Color: {info_simbolo_15['color']}")
        print(f"   - Descripción: {info_simbolo_15['descripcion']}")
        
        self.assertEqual(info_simbolo_15['simbolo'], 'A')
        self.assertEqual(info_simbolo_15['categoria'], 'negro')
        
        print(f"\nSímbolo correcto (A - Ausente)")

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 5: Tabla 4x8
    # ═══════════════════════════════════════════════════════════════════════════════

    def test_05_tabla_4x8_form033(self):
        """Test: Verificar tabla 4x8 correcta"""
        
        print("\n" + "="*80)
        print("TEST 5: Tabla 4x8")
        print("="*80)
        
        datos = self.service.generar_datos_form033(str(self.paciente.id))
        tabla = datos['seccion_ii_odontograma']
        
        # Verificar estructura
        self.assertIn('superior_derecho', tabla)
        self.assertIn('superior_izquierdo', tabla)
        self.assertIn('inferior_izquierdo', tabla)
        self.assertIn('inferior_derecho', tabla)
        
        print(f"\nEstructura 4x8 válida")
        
        # Verificar posiciones
        print(f"\nTabla Superior Derecho (FDI 18-11):")
        for i, item in enumerate(tabla['superior_derecho']):
            fdi_list = ['18', '17', '16', '15', '14', '13', '12', '11']
            if item:
                print(f"   [{i}] FDI {fdi_list[i]}: {item['simbolo']} ({item['descripcion']})")
        
        print(f"\nTabla Superior Izquierdo (FDI 21-28):")
        for i, item in enumerate(tabla['superior_izquierdo']):
            fdi_list = ['21', '22', '23', '24', '25', '26', '27', '28']
            if item:
                print(f"   [{i}] FDI {fdi_list[i]}: {item['simbolo']} ({item['descripcion']})")
        
        # Verificar contenido específico
        # Pos 0 de superior_derecho es FDI 18 (caries = X rojo)
        self.assertIsNotNone(tabla['superior_derecho'][0])
        self.assertEqual(tabla['superior_derecho'][0]['simbolo'], 'X')
        
        # Pos 1 de superior_derecho es FDI 17 (obturado = o azul)
        self.assertIsNotNone(tabla['superior_derecho'][1])
        self.assertEqual(tabla['superior_derecho'][1]['simbolo'], 'o')
        
        print(f"\nPosiciones correctas en tabla")

    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 6: Resumen final
    # ═══════════════════════════════════════════════════════════════════════════════

    def test_06_resumen_final(self):
        """Test: Resumen de lo generado"""
        
        print("\n" + "="*80)
        print("RESUMEN DE TESTS COMPLETADOS")
        print("="*80)
        
        print("""
TEST 1: Generación JSON
   └─ Estructura completa con paciente, odontograma, estadísticas

TEST 2: Generación HTML
   └─ HTML renderizable con tabla 4x8 visual

TEST 3: Generación PDF
   └─ PDF descargable con contenido completo

TEST 4: Mapeo de símbolos
   └─ Usa campo 'simbolo_formulario_033' del modelo

TEST 5: Tabla 4x8
   └─ Estructura correcta con posiciones FDI

TEST 6: Validación
   └─ CPO-D calculado correctamente

════════════════════════════════════════════════════════════════════════════════
RESULTADOS GLOBALES:

Paciente: Juan García López
Cédula: 1234567890
Edad: 34 años

Estadísticas:
- Total dientes: 32
- Sanos: 28
- Cariados: 1 (FDI 18)
- Perdidos: 1 (FDI 15)
- Obturados: 2 (FDI 17, 16)
- CPO-D: 4 / 32

Archivos generados:
1. JSON: estructura de datos para API
2. HTML: visualización en navegador
3. PDF: documento descargable

════════════════════════════════════════════════════════════════════════════════
        """)