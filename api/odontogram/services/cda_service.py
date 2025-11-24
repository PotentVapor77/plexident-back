# api/odontogram/services/cda_service.py

import datetime
import uuid
from lxml import etree
from django.utils import timezone
from django.contrib.auth import get_user_model

from api.patients.models import Paciente
from api.odontogram.models import DiagnosticoDental
from api.odontogram.serializers.fhir_serializers import ClinicalFindingFHIRSerializer


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================


def format_cda_date(date_input) -> str:
    """
    Convierte fecha ISO a formato CDA yyyyMMdd

    Args:
        date_input: str en formato ISO ("1990-05-15" o "1990-05-15T12:30:00")
                o datetime object

    Returns:
        str en formato yyyyMMdd (ej: "19900515")
    """
    if not date_input:
        return ""

    try:
        if isinstance(date_input, str):
            # Maneja ISO format con o sin hora
            if "T" in date_input:
                dt = datetime.datetime.fromisoformat(date_input.replace("Z", "+00:00"))
            else:
                dt = datetime.datetime.strptime(date_input, "%Y-%m-%d")
        else:
            # Si es datetime object
            dt = date_input

        return dt.strftime("%Y%m%d")

    except (ValueError, AttributeError, TypeError) as e:
        print(f"Error convirtiendo fecha '{date_input}': {str(e)}")
        return ""


# ============================================================================
# SERVICIO PRINCIPAL
# ============================================================================


class CDAGenerationService:
    """
    Servicio para generar documentos CDA (Clinical Document Architecture)
    a partir de los datos del odontograma de un paciente.
    """

    # ========================================================================
    # VALIDACIÓN
    # ========================================================================

    def _validate_patient_resource(self, patient_resource: dict) -> None:
        """Valida estructura del recurso Patient FHIR"""
        if not isinstance(patient_resource, dict):
            raise ValueError("Patient resource debe ser dict")

        if not patient_resource.get("identifier"):
            raise ValueError("Patient debe tener identifier")

        if not patient_resource.get("name"):
            raise ValueError("Patient debe tener name")

        if not isinstance(patient_resource["identifier"], list):
            raise ValueError("Patient.identifier debe ser lista")

        if not isinstance(patient_resource["name"], list):
            raise ValueError("Patient.name debe ser lista")

    def _safe_get_nested(self, data, keys, default=None):
        """Extrae valor seguramente de estructura anidada"""
        current = data
        for key in keys:
            if isinstance(current, (dict, list)):
                if isinstance(current, list) and isinstance(key, int):
                    try:
                        current = current[key]
                    except (IndexError, TypeError):
                        return default
                elif isinstance(current, dict):
                    current = current.get(key)
                    if current is None:
                        return default
                else:
                    return default
            else:
                return default
        return current

    # ========================================================================
    # OBTENCIÓN DE DATOS FHIR
    # ========================================================================

    def _get_odontogram_data_as_fhir_bundle(self, patient_id: str) -> dict:
        """
        Obtiene los datos del odontograma y los estructura como un Bundle FHIR.
        """
        try:
            paciente = Paciente.objects.get(id=patient_id)
        except Paciente.DoesNotExist:
            return {}

        # Obtener diagnósticos activos con relaciones
        diagnosticos_qs = DiagnosticoDental.objects.filter(
            superficie__diente__paciente=paciente, activo=True
        ).select_related(
            "diagnostico_catalogo", "superficie__diente__paciente", "odontologo"
        )

        # Serializar hallazgos clínicos a FHIR
        fhir_findings = ClinicalFindingFHIRSerializer(diagnosticos_qs, many=True).data
        bundle_entries = []

        # Crear recurso Paciente
        patient_resource = {
            "resourceType": "Patient",
            "id": str(paciente.id),
            "name": [
                {
                    "use": "official",
                    "family": paciente.apellidos,
                    "given": [paciente.nombres],
                }
            ],
            "identifier": [
                {
                    "system": "urn:oid:1.3.6.1.4.1.21367.13.20.3000.1.1",
                    "value": paciente.cedula_pasaporte,
                }
            ],
            "gender": {"M": "male", "F": "female", "O": "other"}.get(paciente.sexo),
            "birthDate": paciente.fecha_nacimiento.isoformat(),
        }

        bundle_entries.append(
            {"fullUrl": f"urn:uuid:{paciente.id}", "resource": patient_resource}
        )

        # Agregar Practitioners (odontólogos)
        practitioners = {d.odontologo for d in diagnosticos_qs if d.odontologo}

        for pract in practitioners:
            bundle_entries.append(
                {
                    "fullUrl": f"urn:uuid:{pract.id}",
                    "resource": {
                        "resourceType": "Practitioner",
                        "id": str(pract.id),
                        "name": [
                            {"family": pract.apellidos, "given": [pract.nombres]}
                        ],
                    },
                }
            )

        # Agregar hallazgos clínicos (Clinical Findings)
        for finding in fhir_findings:
            bundle_entries.append(
                {"fullUrl": f"urn:uuid:{finding['id']}", "resource": finding}
            )

        # Retornar Bundle FHIR completo
        return {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "type": "document",
            "timestamp": timezone.now().isoformat(),
            "entry": bundle_entries,
        }

    # ========================================================================
    # GENERACIÓN DE CDA XML
    # ========================================================================

    def generate_cda_xml(self, patient_id: str) -> str:
        """
        Genera el documento CDA completo para un paciente y devuelve el XML como string.
        """
        try:
            # Obtener datos FHIR
            fhir_bundle = self._get_odontogram_data_as_fhir_bundle(patient_id)

            if not fhir_bundle.get("entry"):
                raise ValueError("No se encontraron datos para generar el CDA.")

            # Extraer recurso Paciente
            patient_resource = next(
                (
                    e["resource"]
                    for e in fhir_bundle["entry"]
                    if e["resource"]["resourceType"] == "Patient"
                ),
                None,
            )

            if not patient_resource:
                raise ValueError("Recurso Paciente no encontrado en el Bundle FHIR.")

            # Validación
            self._validate_patient_resource(patient_resource)

            # Crear XML root
            nsmap = {
                None: "urn:hl7-org:v3",
                "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            }

            root = etree.Element("ClinicalDocument", nsmap=nsmap)

            # ===================================================================
            # CONSTRUCCIÓN DE LA CABECERA (HEADER)
            # ===================================================================

            now = timezone.now()

            # Realm Code (Ecuador)
            etree.SubElement(root, "realmCode", code="EC")

            # Type ID
            etree.SubElement(
                root, "typeId", root="2.16.840.1.113883.1.3", extension="POCD_HD000040"
            )

            # Template ID
            etree.SubElement(root, "templateId", root="2.16.840.1.113883.10.20.22.1.1")

            # Document ID
            etree.SubElement(
                root,
                "id",
                root="2.16.840.1.113883.19.5.99999.1",
                extension=str(uuid.uuid4()),
            )

            # Document Code (LOINC: Dental findings)
            etree.SubElement(
                root,
                "code",
                code="11459-2",
                codeSystem="2.16.840.1.113883.6.1",
                codeSystemName="LOINC",
                displayName="Dental findings",
            )

            # Document Title
            etree.SubElement(root, "title").text = "Resumen de Odontograma - Plexident"

            # Effective Time
            etree.SubElement(root, "effectiveTime", value=now.strftime("%Y%m%d%H%M%S"))

            # Confidentiality
            etree.SubElement(
                root,
                "confidentialityCode",
                code="N",
                codeSystem="2.16.840.1.113883.5.25",
            )

            # Language
            etree.SubElement(root, "languageCode", code="es-EC")

            # ===================================================================
            # recordTarget - INFORMACIÓN DEL PACIENTE
            # ===================================================================

            record_target = etree.SubElement(root, "recordTarget")
            patient_role = etree.SubElement(record_target, "patientRole")

            # Extracción segura de datos del paciente
            identifier = patient_resource.get("identifier", [{}])[0]
            name = patient_resource.get("name", [{}])[0]

            # ID del paciente (cédula)
            etree.SubElement(
                patient_role,
                "id",
                extension=identifier.get("value", ""),
                root=identifier.get("system", "2.16.840.1.113883.4.1"),
            )

            patient_elem = etree.SubElement(patient_role, "patient")
            name_elem = etree.SubElement(patient_elem, "name")

            # Valores con defaults
            given_name = name.get("given", ["N/A"])[0] if name.get("given") else "N/A"
            family_name = name.get("family", "N/A")

            etree.SubElement(name_elem, "given").text = given_name
            etree.SubElement(name_elem, "family").text = family_name

            # Género
            etree.SubElement(
                patient_elem,
                "administrativeGenderCode",
                code=patient_resource.get("gender", "UN").upper(),
                codeSystem="2.16.840.1.113883.5.1",
            )

            # Fecha de nacimiento
            etree.SubElement(
                patient_elem,
                "birthTime",
                value=format_cda_date(patient_resource.get("birthDate", "")),
            )

            # ===================================================================
            # author - INFORMACIÓN DEL AUTOR/SISTEMA
            # ===================================================================

            author = etree.SubElement(root, "author")
            etree.SubElement(author, "time", value=now.strftime("%Y%m%d%H%M%S"))

            assigned_author = etree.SubElement(author, "assignedAuthor")
            etree.SubElement(
                assigned_author,
                "id",
                root="2.16.840.1.113883.4.6",
                extension="PLEXIDENT_SYSTEM_ID",
            )

            author_person = etree.SubElement(assigned_author, "assignedPerson")
            author_name = etree.SubElement(author_person, "name")
            etree.SubElement(author_name, "given").text = "Plexident"
            etree.SubElement(author_name, "family").text = "System"

            # ===================================================================
            # custodian - INFORMACIÓN DE LA ORGANIZACIÓN
            # ===================================================================

            custodian = etree.SubElement(root, "custodian")
            assigned_custodian = etree.SubElement(custodian, "assignedCustodian")
            represented_custodian_org = etree.SubElement(
                assigned_custodian, "representedCustodianOrganization"
            )

            etree.SubElement(
                represented_custodian_org,
                "id",
                root="2.16.840.1.113883.4.6",
                extension="CLINIC_ID",
            )

            etree.SubElement(represented_custodian_org, "name").text = (
                "Plexident Dental Clinic"
            )

            # ===================================================================
            # CONSTRUCCIÓN DEL CUERPO (BODY)
            # ===================================================================

            component = etree.SubElement(root, "component")
            structured_body = etree.SubElement(component, "structuredBody")

            self._build_dental_findings_section(structured_body, fhir_bundle)

            # ===================================================================
            # SERIALIZACIÓN A STRING
            # ===================================================================

            try:
                cda_xml = etree.tostring(
                    root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
                )
                return cda_xml.decode("utf-8")

            except (etree.XMLSyntaxError, UnicodeDecodeError) as e:
                raise ValueError(f"Error serializando CDA XML: {str(e)}")

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error generando CDA: {str(e)}")

    def _build_dental_findings_section(self, structured_body, fhir_bundle):
        """Construye la sección de hallazgos odontológicos en el CDA"""
        component_section = etree.SubElement(structured_body, "component")
        section = etree.SubElement(component_section, "section")

        # Código LOINC para hallazgos dentales
        etree.SubElement(
            section,
            "code",
            code="11459-2",
            codeSystem="2.16.840.1.113883.6.1",
            displayName="Dental findings",
        )

        etree.SubElement(section, "title").text = "Hallazgos Odontológicos"

        # Texto narrativo
        text_elem = etree.SubElement(section, "text")

        # Construir texto narrativo de diagnósticos
        text_content = "Diagnósticos del odontograma:\n"

        for entry in fhir_bundle.get("entry", []):
            if entry["resource"].get("resourceType") == "Observation":
                code_display = (
                    entry["resource"].get("code", {}).get("text", "Diagnóstico")
                )
                status = entry["resource"].get("status", "final")
                text_content += f"\n- {code_display} (Estado: {status})"

        text_elem.text = (
            text_content if len(text_content) > 40 else "Sin diagnósticos registrados"
        )

        # Entries (Observaciones)
        for entry in fhir_bundle.get("entry", []):
            if entry["resource"].get("resourceType") == "Observation":
                self._build_observation_entry(section, entry["resource"])

    def _build_observation_entry(self, section, observation):
        """Construye una entrada de observación en la sección"""
        entry = etree.SubElement(section, "entry")
        act = etree.SubElement(entry, "observation", classCode="OBS", moodCode="EVN")

        # ID
        etree.SubElement(
            act,
            "id",
            root="2.16.840.1.113883.4.6",
            extension=observation.get("id", str(uuid.uuid4())),
        )

        # Código
        code = observation.get("code", {})
        etree.SubElement(
            act,
            "code",
            code=code.get("coding", [{}])[0].get("code", ""),
            displayName=code.get("text", ""),
        )

        # Estado
        etree.SubElement(act, "statusCode", code=observation.get("status", "final"))

        # Valor
        if observation.get("valueString"):
            value_elem = etree.SubElement(act, "value", xsi_type="ST")
            value_elem.text = observation["valueString"]


if __name__ == "__main__":
    """
    Ejemplo de cómo usar el servicio:

    service = CDAGenerationService()
    cda_xml = service.generate_cda_xml(patient_id="123")
    print(cda_xml)
    """
    pass
