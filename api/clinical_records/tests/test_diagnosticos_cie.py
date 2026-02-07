import pytest
from unittest.mock import Mock, patch
from django.utils import timezone
from django.core.exceptions import ValidationError
from api.odontogram.models import DiagnosticoDental
from api.clinical_records.models.clinical_record import ClinicalRecord
from models.diagnostico_cie import DiagnosticoCIEHistorial
from api.clinical_records.services.diagnostico_cie_service import DiagnosticosCIEService


@pytest.fixture
def paciente():
    return Mock(id="paciente-uuid", activo=True)


@pytest.fixture
def usuario():
    user = Mock()
    user.username = "testuser"
    user.id = 1
    return user


@pytest.fixture
def historial_abierto():
    hc = Mock(spec=ClinicalRecord)
    hc.id = "historial-uuid"
    hc.estado = "BORRADOR"  # Estado abierto
    hc.activo = True
    hc.diagnosticosciecargados = False
    hc.tipo_cargadiagnosticos = None
    hc.save = Mock()
    return hc


@pytest.fixture
def diagnostico_dental_valido():
    dd = Mock(spec=DiagnosticoDental)
    dd.id = "dd-uuid"
    dd.activo = True
    dd.fecha = timezone.now()
    catalogo = Mock()
    catalogo.codigoicd10 = "K00.0"
    catalogo.nombre = "Caries"
    catalogo.siglas = "Caries"
    dd.diagnosticocatalogo = catalogo
    superficie = Mock()
    superficie.getnombredisplay.return_value = "Oclusal 16"
    diente = Mock()
    diente.codigofdi = "16"
    superficie.diente = diente
    dd.superficie = superficie
    return dd


class TestDiagnosticosCIEService:
    """Tests para DiagnosticosCIEService."""

    @patch(
        "api.clinicalrecords.services.diagnostico_cie_service.DiagnosticoDental.objects.filter"
    )
    @patch(
        "api.clinicalrecords.services.diagnostico_cie_service.DiagnosticoCIEHistorial.objects.filter"
    )
    def test_obtenerdiagnosticosnuevos(self, mock_cie_historial, mock_dental, paciente):
        """Prueba obtener diagnósticos nuevos (no cargados previamente)."""
        # Mock todos los diagnósticos dentales
        mock_dental.return_value.select_related.return_value = [
            self.diagnostico_dental_valido()
        ]
        # Mock algunos ya cargados
        mock_cie_historial.return_value.values_list.return_value = ["otro-dd-id"]

        result = DiagnosticosCIEService.obtenerdiagnosticosnuevospacienteid(paciente.id)

        assert len(result) == 1
        diag = result[0]
        assert diag["codigocie"] == "K00.0"
        assert diag["dientefdi"] == "16"
        assert diag["tipocie"] == "PRE"

    @patch(
        "api.clinicalrecords.services.diagnostico_cie_service.DiagnosticoDental.objects.filter"
    )
    def test_obtenerdiagnosticostodos(self, mock_dental, paciente):
        """Prueba obtener todos los diagnósticos activos."""
        mock_dental.return_value.select_related.return_value.order_by.return_value = [
            self.diagnostico_dental_valido()
        ]

        result = DiagnosticosCIEService.obtenerdiagnosticostodospacienteid(paciente.id)

        assert len(result) == 1
        assert result[0]["diagnosticonombre"] == "Caries"

    def test_cargardiagnosticosahistorial_exito(
        self, historial_abierto, usuario, diagnostico_dental_valido
    ):
        """Prueba carga exitosa de diagnósticos a historial abierto."""
        diagnosticos_data = [
            {"diagnosticodentalid": diagnostico_dental_valido.id, "tipocie": "PRE"}
        ]

        with patch(
            "api.clinicalrecords.services.diagnostico_cie_service.DiagnosticoDental.objects.get"
        ) as mock_get:
            with patch(
                "api.clinicalrecords.services.diagnostico_cie_service.DiagnosticoCIEHistorial.objects.create"
            ) as mock_create:
                mock_get.return_value = diagnostico_dental_valido
                result = DiagnosticosCIEService.cargardiagnosticosahistorial(
                    historial_abierto, diagnosticos_data, "nuevos", usuario
                )

        assert result["success"] is True
        assert result["totaldiagnosticos"] == 1
        assert historial_abierto.diagnosticosciecargados is True

    def test_cargardiagnosticos_historial_cerrado(self, historial_abierto, usuario):
        """Prueba falla si historial está cerrado."""
        historial_abierto.estado = "CERRADO"
        diagnosticos_data = [{"diagnosticodentalid": "dd-uuid"}]

        with pytest.raises(
            ValueError, match="No se pueden agregar diagnósticos a un historial cerrado"
        ):
            DiagnosticosCIEService.cargardiagnosticosahistorial(
                historial_abierto, diagnosticos_data, "nuevos", usuario
            )

    def test_eliminardiagnosticoindividual_exito(self, usuario):
        """Prueba eliminación lógica de diagnóstico individual."""
        diagnostico = Mock(spec=DiagnosticoCIEHistorial)
        diagnostico.id = "cie-uuid"
        diagnostico.activo = True
        diagnostico.historialclinico = Mock(estado="BORRADOR")
        diagnostico.save = Mock()

        with patch(
            "api.clinicalrecords.services.diagnostico_cie_service.DiagnosticoCIEHistorial.objects.get",
            return_value=diagnostico,
        ):
            result = DiagnosticosCIEService.eliminardiagnosticoindividual(
                "cie-uuid", usuario
            )

        assert result["success"] is True
        diagnostico.activo.assert_called_once_with(False)

    def test_actualizartipocieindividual_exito(self, usuario):
        """Prueba actualización de tipo CIE (PRE/DEF)."""
        diagnostico = Mock(spec=DiagnosticoCIEHistorial)
        diagnostico.id = "cie-uuid"
        diagnostico.activo = True
        diagnostico.historialclinico = Mock(estado="BORRADOR")
        diagnostico.gettipociedisplay.return_value = "Definido"
        diagnostico.save = Mock()

        with patch(
            "api.clinicalrecords.services.diagnostico_cie_service.DiagnosticoCIEHistorial.objects.get",
            return_value=diagnostico,
        ):
            result = DiagnosticosCIEService.actualizartipocieindividual(
                "cie-uuid", "DEF", usuario
            )

        assert result["success"] is True
        assert result["tipocie"] == "DEF"

    def test_sincronizardiagnosticoshistorial(self, historial_abierto, usuario):
        """Prueba sincronización: desactiva extras, crea/actualiza."""
        diagnosticos_finales = [{"diagnosticodentalid": "dd-uuid", "tipocie": "PRE"}]

        with patch(
            "api.clinicalrecords.services.diagnostico_cie_service.ClinicalRecord.objects.get",
            return_value=historial_abierto,
        ):
            with patch(
                "api.clinicalrecords.services.diagnostico_cie_service.DiagnosticoDental.objects.get"
            ) as mock_get_dd:
                with patch(
                    "api.clinicalrecords.services.diagnostico_cie_service.DiagnosticoCIEHistorial.objects.filter"
                ) as mock_filter:
                    mock_get_dd.return_value = self.diagnostico_dental_valido()
                    mock_filter.first.return_value = None  # No existe previo
                    with patch(
                        "api.clinicalrecords.services.diagnostico_cie_service.DiagnosticoCIEHistorial.objects.create"
                    ) as mock_create:
                        result = (
                            DiagnosticosCIEService.sincronizardiagnosticoshistorial(
                                historial_abierto.id,
                                diagnosticos_finales,
                                "todos",
                                usuario,
                            )
                        )

        assert result["success"] is True
        assert result["totaldiagnosticos"] == 1
