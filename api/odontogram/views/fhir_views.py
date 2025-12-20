from jsonschema import ValidationError as JSONSchemaValidationError

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from datetime import datetime
import logging

from api.patients.models import Paciente
from api.odontogram.models import DiagnosticoDental
from api.odontogram.serializers.fhir_serializers import (
    FHIRPatientReferenceSerializer,
    ClinicalFindingFHIRSerializer,
    FHIRPractitionerReferenceSerializer,
)
from api.odontogram.services.fhir_serializers import FHIRService

logger = logging.getLogger(__name__)


class FHIRViewSet(viewsets.ViewSet):
    """
    FHIR R4 API

    GET  /api/odontogram/fhir/patient/{id}/
    GET  /api/odontogram/fhir/odontograma/{paciente_id}/
    GET  /api/odontogram/fhir/cda/{paciente_id}/
    POST /api/odontogram/fhir/validate/
    GET  /api/odontogram/fhir/search/
    """

    permission_classes = [IsAuthenticated]

    # ==================== PATIENT ====================

    @method_decorator(cache_page(60 * 5))  # Cache 5 minutos
    def patient(self, request, pk=None):
        """
        Retorna datos del paciente en formato FHIR Patient Resource

        GET /api/odontogram/fhir/patient/{id}/
        """
        try:
            paciente = Paciente.objects.get(id=pk)
        except Paciente.DoesNotExist:
            logger.warning(f"Paciente no encontrado: {pk}")
            return Response(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {
                            "severity": "error",
                            "code": "not-found",
                            "diagnostics": f"Paciente {pk} no encontrado",
                        }
                    ],
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            serializer = FHIRPatientReferenceSerializer(paciente)
            logger.info(f"FHIR Patient GET: {pk}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error en FHIR Patient: {str(e)}")
            return Response(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {
                            "severity": "error",
                            "code": "exception",
                            "diagnostics": str(e),
                        }
                    ],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ==================== ODONTOGRAMA BUNDLE ====================

    def odontograma(self, request, paciente_id=None):
        """
        GET /api/odontogram/fhir/odontograma/{paciente_id}/
        Retorna un Bundle FHIR con el odontograma del paciente.
        """
        try:
            paciente = Paciente.objects.get(id=paciente_id)

            # Obtener diagnósticos del odontograma
            diagnosticos = (
                DiagnosticoDental.objects.filter(
                    superficie__diente__paciente=paciente
                )
                .select_related("odontologo", "superficie__diente")
            )

            # Crear FHIR Bundle
            bundle = FHIRService.crear_bundle_odontograma(
                paciente=paciente,
                diagnosticos=diagnosticos,
            )

            logger.info(
                f"FHIR Odontograma Bundle GET: paciente={paciente_id}, "
                f"entries={len(bundle.get('entry', []))}"
            )
            return Response(bundle, status=status.HTTP_200_OK)

        except Paciente.DoesNotExist:
            logger.warning(f"Paciente no encontrado para odontograma: {paciente_id}")
            return Response(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {
                            "severity": "error",
                            "code": "not-found",
                            "diagnostics": f"Paciente {paciente_id} no encontrado",
                        }
                    ],
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error creando Bundle: {str(e)}")
            return Response(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {
                            "severity": "error",
                            "code": "exception",
                            "diagnostics": str(e),
                        }
                    ],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ==================== CDA DOCUMENT ====================

    def cda(self, request, paciente_id=None):
        """
        GET /api/odontogram/fhir/cda/{paciente_id}/

        Retorna documento CDA como FHIR Binary Resource en Bundle tipo "document".
        """
        try:
            paciente = Paciente.objects.get(id=paciente_id)

            # Generar CDA
            from api.odontogram.services.cda_service import CDAGenerationService

            cda_service = CDAGenerationService()
            cda_xml = cda_service.generate_cda_xml(str(paciente_id))

            # Encodear a base64
            import base64

            cda_base64 = base64.b64encode(cda_xml.encode("utf-8")).decode("utf-8")

            # Crear Bundle
            bundle = {
                "resourceType": "Bundle",
                "type": "document",
                "timestamp": datetime.now().isoformat(),
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Binary",
                            "contentType": "application/xml+cda",
                            "data": cda_base64,
                            "meta": {
                                "profile": [
                                    "http://hl7.org/fhir/StructureDefinition/Binary"
                                ],
                                "lastUpdated": datetime.now().isoformat(),
                            },
                        }
                    }
                ],
            }

            logger.info(f"FHIR CDA Bundle GET: paciente={paciente_id}")
            return Response(bundle, status=status.HTTP_200_OK)

        except Paciente.DoesNotExist:
            logger.warning(f"Paciente no encontrado para CDA: {paciente_id}")
            return Response(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {
                            "severity": "error",
                            "code": "not-found",
                            "diagnostics": f"Paciente {paciente_id} no encontrado",
                        }
                    ],
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error generando CDA: {str(e)}")
            return Response(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {
                            "severity": "error",
                            "code": "exception",
                            "diagnostics": str(e),
                        }
                    ],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ==================== VALIDATION ====================

    @action(detail=False, methods=["post"])
    def validate(self, request):
        """
        POST /api/odontogram/fhir/validate/

        Valida un recurso FHIR contra el profile correspondiente.

        Body:
        {
            "resource": { ... FHIR Resource ... },
            "profile": "http://hl7.org/fhir/StructureDefinition/Patient"
        }
        """
        try:
            resource = request.data.get("resource")
            profile = request.data.get("profile")

            if not resource or not profile:
                # Esto lo formateará el custom_exception_handler a la estructura estándar
                from rest_framework.exceptions import ValidationError

                raise ValidationError(
                    {"detail": 'Requiere "resource" y "profile" en el cuerpo de la petición'}
                )

            # Validar usando jsonschema (o la lógica interna de FHIRService)
            valid, issues = FHIRService.validar_recurso_fhir(
                resource=resource,
                profile=profile,
            )

            logger.info(f"FHIR Validation: valid={valid}, issues={len(issues)}")
            return Response(
                {
                    "valid": valid,
                    "issues": issues,
                    "resource_type": resource.get("resourceType"),
                    "timestamp": datetime.now().isoformat(),
                },
                status=status.HTTP_200_OK,
            )

        except JSONSchemaValidationError as e:
            logger.error(f"Error de validación JSONSchema: {str(e)}")
            return Response(
                {
                    "valid": False,
                    "issues": [str(e)],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error en validación FHIR: {str(e)}")
            return Response(
                {
                    "valid": False,
                    "issues": [str(e)],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ==================== SEARCH ====================

    @action(detail=False, methods=["get"])
    def search(self, request):
        """
        GET /api/odontogram/fhir/search/?patient={id}&code={snomed}&_count={limit}

        Busca recursos FHIR según parámetros y retorna un Bundle searchset.
        """
        try:
            patient_id = request.query_params.get("patient")
            code = request.query_params.get("code")
            limit = int(request.query_params.get("_count", 10))

            results = FHIRService.buscar_recursos(
                patient_id=patient_id,
                code=code,
                limit=limit,
            )

            bundle = {
                "resourceType": "Bundle",
                "type": "searchset",
                "total": len(results),
                "entry": results,
            }

            return Response(bundle, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error en búsqueda FHIR: {str(e)}")
            return Response(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [
                        {
                            "severity": "error",
                            "code": "exception",
                            "diagnostics": str(e),
                        }
                    ],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
