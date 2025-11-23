from xml.etree import ElementTree as ET
from datetime import datetime
from django.utils import timezone
import xml.dom.minidom


class CDAOdontogramGenerator:
    """
    Generador de documentos CDA v3 desde odontogramas.
    
    CDA = Clinical Document Architecture (HL7 v3)
    Formato: XML estructurado para interoperabilidad de documentos clínicos.
    
    Este generator es compatible con:
    - CDA v3 Release 2
    - Ecuador MSP
    - Normativa HL7
    """
    
    def __init__(self, paciente, odontologo=None):
        self.paciente = paciente
        self.odontologo = odontologo
    
    def generar_cda(self):
        """
        Genera el documento CDA completo.
        Retorna: string XML válido y formateado
        """
        # Crear raíz del documento CDA
        root = self._create_root()
        
        # Metadata del documento
        self._add_document_metadata(root)
        
        # Información del paciente
        self._add_record_target(root)
        
        # Autor (odontólogo)
        self._add_author(root)
        
        # Custodio/Institución
        self._add_custodian(root)
        
        # Información legal
        self._add_legal_authenticator(root)
        
        # Cuerpo del documento
        self._add_component(root)
        
        # Convertir a string con formato
        return self._prettify_xml(root)
    
    def _create_root(self):
        """Crea el elemento raíz CDA"""
        root = ET.Element('ClinicalDocument', {
            'xmlns': 'urn:hl7-org:v3',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': 'urn:hl7-org:v3 CDA.xsd'
        })
        return root
    
    def _add_document_metadata(self, root):
        """Agrega metadata del documento"""
        # Código del documento
        ET.SubElement(root, 'realmCode', {'code': 'EC'})
        
        ET.SubElement(root, 'typeId', {
            'root': '2.16.840.1.113883.1.3',
            'extension': 'POCD_HD000040'
        })
        
        # Template ID (Odontología)
        ET.SubElement(root, 'templateId', {
            'root': '2.16.840.1.113883.10.12.1',
            'assigningAuthorityName': 'HL7 Dental'
        })
        
        # ID del documento (OID)
        ET.SubElement(root, 'id', {
            'root': '2.16.840.1.113883.3.933',
            'extension': f"ODO-{self.paciente.id}-{int(timezone.now().timestamp())}"
        })
        
        # Tipo de documento (LOINC)
        ET.SubElement(root, 'code', {
            'code': '11526-1',
            'codeSystem': '2.16.840.1.113883.6.1',
            'displayName': 'Dental Records'
        })
        
        # Título
        title = ET.SubElement(root, 'title')
        title.text = f"Registro Odontológico - {self.paciente.nombres} {self.paciente.apellidos}"
        
        # Timestamp del documento
        now = timezone.now()
        effective_time = ET.SubElement(root, 'effectiveTime')
        effective_time.set('value', now.strftime('%Y%m%d%H%M%S'))
        
        # Confidencialidad
        ET.SubElement(root, 'confidentialityCode', {
            'code': 'N',
            'codeSystem': '2.16.840.1.113883.5.25'
        })
        
        # Idioma
        ET.SubElement(root, 'languageCode', {'code': 'es-EC'})
        
        # Versión
        ET.SubElement(root, 'versionNumber', {'value': '1'})
    
    def _add_record_target(self, root):
        """Agrega información del paciente (RecordTarget)"""
        record_target = ET.SubElement(root, 'recordTarget')
        patient_role = ET.SubElement(record_target, 'patientRole')
        
        # ID del paciente
        ET.SubElement(patient_role, 'id', {
            'root': '2.16.840.1.113883.3.933',
            'extension': str(self.paciente.id)
        })
        
        # Información del paciente
        patient = ET.SubElement(patient_role, 'patient')
        
        # Nombre
        name = ET.SubElement(patient, 'name')
        given = ET.SubElement(name, 'given')
        given.text = self.paciente.nombres
        family = ET.SubElement(name, 'family')
        family.text = self.paciente.apellidos
        
        # Género
        if hasattr(self.paciente, 'sexo') and self.paciente.sexo:
            gender_map = {'M': 'M', 'F': 'F', 'O': 'UN'}
            gender_code = gender_map.get(self.paciente.sexo[0].upper(), 'UN')
            ET.SubElement(patient, 'administrativeGenderCode', {
                'code': gender_code,
                'codeSystem': '2.16.840.1.113883.5.1'
            })
        
        # Fecha de nacimiento
        if hasattr(self.paciente, 'fecha_nacimiento') and self.paciente.fecha_nacimiento:
            birth_time = ET.SubElement(patient, 'birthTime')
            birth_time.set('value', self.paciente.fecha_nacimiento.strftime('%Y%m%d'))
    
    def _add_author(self, root):
        """Agrega información del autor (odontólogo)"""
        author = ET.SubElement(root, 'author')
        
        # Timestamp
        time = ET.SubElement(author, 'time')
        time.set('value', timezone.now().strftime('%Y%m%d%H%M%S'))
        
        # Assigned Author
        assigned_author = ET.SubElement(author, 'assignedAuthor')
        ET.SubElement(assigned_author, 'id', {
            'root': '2.16.840.1.113883.3.933',
            'extension': str(self.odontologo.id) if self.odontologo else 'unknown'
        })
        
        # Profesional
        if self.odontologo:
            assigned_person = ET.SubElement(assigned_author, 'assignedPerson')
            name = ET.SubElement(assigned_person, 'name')
            given = ET.SubElement(name, 'given')
            given.text = self.odontologo.first_name
            family = ET.SubElement(name, 'family')
            family.text = self.odontologo.last_name
    
    def _add_custodian(self, root):
        """Agrega información de custodia (institución)"""
        custodian = ET.SubElement(root, 'custodian')
        assigned_custodian = ET.SubElement(custodian, 'assignedCustodian')
        
        representation_org = ET.SubElement(assigned_custodian, 'representedCustodianOrganization')
        ET.SubElement(representation_org, 'id', {
            'root': '2.16.840.1.113883.3.933',
            'extension': 'plexident'
        })
        
        name = ET.SubElement(representation_org, 'name')
        name.text = 'Plexident - Sistema de Gestión Odontológica'
    
    def _add_legal_authenticator(self, root):
        """Agrega autenticidad legal del documento"""
        legal_auth = ET.SubElement(root, 'legalAuthenticator')
        legal_auth.set('time', timezone.now().strftime('%Y%m%d%H%M%S'))
        
        signature_code = ET.SubElement(legal_auth, 'signatureCode')
        signature_code.set('code', 'S')
        
        assigned_entity = ET.SubElement(legal_auth, 'assignedEntity')
        ET.SubElement(assigned_entity, 'id', {
            'root': '2.16.840.1.113883.3.933'
        })
    
    def _add_component(self, root):
        """Agrega el cuerpo del documento con datos clínicos"""
        component = ET.SubElement(root, 'component')
        structured_body = ET.SubElement(component, 'structuredBody')
        
        # Sección: Odontograma
        self._add_odontogram_section(structured_body)
        
        # Sección: Diagnósticos
        self._add_diagnosis_section(structured_body)
        
        # Sección: Plan de Tratamiento
        self._add_treatment_plan_section(structured_body)
    
    def _add_odontogram_section(self, body):
        """Sección del odontograma en CDA"""
        section = ET.SubElement(body, 'section')
        
        # Code (LOINC para odontograma)
        ET.SubElement(section, 'code', {
            'code': '11525-5',
            'codeSystem': '2.16.840.1.113883.6.1',
            'displayName': 'Odontograma'
        })
        
        # Title
        title = ET.SubElement(section, 'title')
        title.text = 'Odontograma'
        
        # Text (descripción)
        text = ET.SubElement(section, 'text')
        
        # Tabla de dientes
        table = ET.SubElement(text, 'table', {'width': '100%', 'border': '1'})
        
        # Header
        thead = ET.SubElement(table, 'thead')
        tr = ET.SubElement(thead, 'tr')
        ET.SubElement(tr, 'th').text = 'Diente (FDI)'
        ET.SubElement(tr, 'th').text = 'Superficie'
        ET.SubElement(tr, 'th').text = 'Diagnóstico'
        ET.SubElement(tr, 'th').text = 'Observaciones'
        
        # Body
        tbody = ET.SubElement(table, 'tbody')
        
        if hasattr(self.paciente, 'dientes'):
            for diente in self.paciente.dientes.all():
                for superficie in diente.superficies.all():
                    for diagnostico in superficie.diagnosticos.all():
                        tr = ET.SubElement(tbody, 'tr')
                        ET.SubElement(tr, 'td').text = str(diente.codigo_fdi)
                        ET.SubElement(tr, 'td').text = superficie.get_nombre_display()
                        ET.SubElement(tr, 'td').text = diagnostico.diagnostico_catalogo.nombre
                        ET.SubElement(tr, 'td').text = diagnostico.descripcion or '-'
    
    def _add_diagnosis_section(self, body):
        """Sección de diagnósticos dentales en CDA"""
        section = ET.SubElement(body, 'section')
        
        ET.SubElement(section, 'code', {
            'code': '11450-4',
            'codeSystem': '2.16.840.1.113883.6.1',
            'displayName': 'Diagnósticos Dentales'
        })
        
        title = ET.SubElement(section, 'title')
        title.text = 'Diagnósticos Dentales'
        
        # Entradas por diagnóstico
        if hasattr(self.paciente, 'dientes'):
            for diente in self.paciente.dientes.all():
                for superficie in diente.superficies.all():
                    for diagnostico in superficie.diagnosticos.all():
                        entry = ET.SubElement(section, 'entry')
                        observation = ET.SubElement(entry, 'observation')
                        observation.set('classCode', 'OBS')
                        observation.set('moodCode', 'EVN')
                        
                        ET.SubElement(observation, 'statusCode', {'code': 'completed'})
                        
                        code = ET.SubElement(observation, 'code')
                        code.set('code', diagnostico.diagnostico_catalogo.codigo_fhir or 'unknown')
                        code.set('codeSystem', '2.16.840.1.113883.6.96')  # SNOMED-CT
                        code.set('displayName', diagnostico.diagnostico_catalogo.nombre)
                        
                        value = ET.SubElement(observation, 'value')
                        value.set('xsi:type', 'CD')
                        value.set('code', diagnostico.diagnostico_catalogo.codigo_icd10 or 'unknown')
                        value.set('codeSystem', '2.16.840.1.113883.6.90')  # ICD-10-CM
                        value.set('displayName', diagnostico.diagnostico_catalogo.nombre)
    
    def _add_treatment_plan_section(self, body):
        """Sección de plan de tratamiento en CDA"""
        section = ET.SubElement(body, 'section')
        
        ET.SubElement(section, 'code', {
            'code': '11492-0',
            'codeSystem': '2.16.840.1.113883.6.1',
            'displayName': 'Plan de Tratamiento'
        })
        
        title = ET.SubElement(section, 'title')
        title.text = 'Plan de Tratamiento'
        
        text = ET.SubElement(section, 'text')
        text.text = 'Plan de tratamiento odontológico a ser completado en próximas sesiones.'
    
    def _prettify_xml(self, elem):
        """Formatea el XML para ser legible"""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = xml.dom.minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")


# USO DEL GENERATOR:
# ==================
#
# from api.odontogram.generators.cda_generator import CDAOdontogramGenerator
# from api.patients.models import Paciente
#
# paciente = Paciente.objects.get(id=1)
# odontologo = request.user  # El usuario logueado
#
# generator = CDAOdontogramGenerator(paciente, odontologo)
# cda_xml = generator.generar_cda()
#
# # Guardar en archivo
# with open('odontograma.xml', 'w') as f:
#     f.write(cda_xml)
#
# # O retornar en response
# from django.http import HttpResponse
#
# response = HttpResponse(cda_xml, content_type='application/xml')
# response['Content-Disposition'] = 'attachment; filename="odontograma.xml"'
# return response
