# api/clinical_records/serializers/diagnosticos_cie_serializers.py
import re
from rest_framework import serializers
from api.odontogram.models import DiagnosticoDental
from api.odontogram.serializers.diagnostico_cie_serializer import DiagnosticoCIESerializer

# ---------------------------------------------------------------------------
# Validador de formato CIE-10 (reutilizable)
# ---------------------------------------------------------------------------

_CIE10_RE = re.compile(r'^[A-Z][0-9]{2}(\.[0-9A-Za-z]{1,4})?$', re.IGNORECASE)


def validar_formato_cie10(value: str) -> str:
    """Valida que el valor tenga un formato CIE-10 aceptable. Ej: K08, K08.1"""
    value = value.strip().upper()
    if not _CIE10_RE.match(value):
        raise serializers.ValidationError(
            f'"{value}" no tiene un formato CIE-10 válido. '
            'Use: letra + 2 dígitos + (opcional) punto + 1-4 caracteres. Ej: K08.1'
        )
    return value


# ---------------------------------------------------------------------------
# Serializer principal (requerido por clinical_record.py)
# ---------------------------------------------------------------------------

class WritableDiagnosticoCIEHistorialSerializer(serializers.Serializer):
    """Serializer flexible para guardar múltiples diagnósticos CIE"""

    # Campos de entrada (escritura)
    diagnosticos = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        help_text="Lista de diagnósticos con IDs y tipos"
    )

    diagnosticos_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        help_text="Alternativa: lista simple de IDs"
    )

    tipo_carga = serializers.ChoiceField(
        choices=[
            ('nuevos', 'Solo nuevos diagnósticos'),
            ('todos', 'Todos los diagnósticos del snapshot'),
        ],
        required=True
    )

    def validate(self, data):
        """Validar que se proporcione al menos un formato de diagnósticos"""
        if not data.get('diagnosticos') and not data.get('diagnosticos_ids'):
            raise serializers.ValidationError(
                'Debe proporcionar "diagnosticos" o "diagnosticos_ids"'
            )

        # Validar código personalizado en cada diagnóstico si se envía
        for diag in data.get('diagnosticos') or []:
            codigo = diag.get('codigo_cie_personalizado')
            if codigo and codigo.strip():
                try:
                    validar_formato_cie10(codigo)
                except serializers.ValidationError as exc:
                    raise serializers.ValidationError(
                        f"diagnostico_dental_id {diag.get('diagnostico_dental_id')}: {exc.detail}"
                    )

        return data

    def to_representation(self, instance):
        """Para serialización de salida"""
        if isinstance(instance, dict):
            return instance

        try:
            diagnosticos = instance.diagnosticos.all() if hasattr(instance, 'diagnosticos') else []
            diagnosticos_serializer = DiagnosticoCIESerializer(diagnosticos, many=True)
            return {
                'diagnosticos': diagnosticos_serializer.data,
                'tipo_carga': getattr(instance, 'tipo_carga_diagnosticos', 'todos'),
                'diagnosticos_ids': [str(d.id) for d in diagnosticos]
            }
        except AttributeError:
            return {
                'diagnosticos': [],
                'tipo_carga': 'todos',
                'diagnosticos_ids': []
            }

    def create(self, validated_data):
        """Crear registro de diagnósticos CIE"""
        historial_clinico = self.context.get('historial_clinico')
        creado_por = self.context.get('request').user if self.context.get('request') else None
        tipo_carga = validated_data['tipo_carga']

        diagnosticos_ids = []

        if validated_data.get('diagnosticos_ids'):
            diagnosticos_ids = validated_data['diagnosticos_ids']
        elif validated_data.get('diagnosticos'):
            diagnosticos_ids = [
                diag.get('diagnostico_dental_id') or diag.get('diagnostico_dental', {}).get('id')
                for diag in validated_data['diagnosticos']
                if diag
            ]
            diagnosticos_ids = [did for did in diagnosticos_ids if did]

        diagnosticos = DiagnosticoDental.objects.filter(
            id__in=diagnosticos_ids,
            activo=True
        ).select_related(
            'diagnostico_catalogo',
            'superficie',
            'superficie__diente',
            'superficie__diente__paciente',
            'odontologo'
        )

        serializer = DiagnosticoCIESerializer(diagnosticos, many=True)

        return {
            'diagnosticos': serializer.data,
            'tipo_carga': tipo_carga,
            'diagnosticos_ids': diagnosticos_ids,
            'total': diagnosticos.count()
        }