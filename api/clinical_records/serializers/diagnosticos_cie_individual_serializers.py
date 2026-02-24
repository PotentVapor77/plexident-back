# api/clinical_records/serializers/diagnosticos_cie_individual_serializers.py
import re
from rest_framework import serializers
from api.clinical_records.models import DiagnosticoCIEHistorial

# ---------------------------------------------------------------------------
# Validador de formato CIE-10 (compartido con diagnosticos_cie_serializers.py)
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
# Serializers
# ---------------------------------------------------------------------------

class DiagnosticoCIEIndividualSerializer(serializers.ModelSerializer):
    """Serializer para gestión individual de diagnósticos CIE"""

    diagnostico_nombre = serializers.CharField(source='nombre_diagnostico', read_only=True)
    # codigo_cie ahora devuelve el valor efectivo (personalizado o catálogo)
    codigo_cie = serializers.CharField(read_only=True)
    # Campos nuevos de personalización
    codigo_cie_original = serializers.CharField(read_only=True)
    tiene_codigo_personalizado = serializers.BooleanField(read_only=True)
    diente_fdi = serializers.CharField(read_only=True)
    superficie_nombre = serializers.CharField(read_only=True)
    tipo_cie_display = serializers.CharField(source='get_tipo_cie_display', read_only=True)

    class Meta:
        model = DiagnosticoCIEHistorial
        fields = [
            'id',
            'diagnostico_dental',
            'diagnostico_nombre',
            'codigo_cie',
            'codigo_cie_original',
            'codigo_cie_personalizado',
            'tiene_codigo_personalizado',
            'diente_fdi',
            'superficie_nombre',
            'tipo_cie',
            'tipo_cie_display',
            'activo',
            'fecha_creacion',
            'fecha_modificacion',
            'creado_por',
            'actualizado_por',
        ]
        read_only_fields = [
            'id',
            'diagnostico_dental',
            'historial_clinico',
            'diagnostico_nombre',
            'codigo_cie',
            'codigo_cie_original',
            'tiene_codigo_personalizado',
            'diente_fdi',
            'superficie_nombre',
            'fecha_creacion',
            'fecha_modificacion',
            'creado_por',
            'actualizado_por',
        ]


class DiagnosticoCIEUpdateSerializer(serializers.Serializer):
    """Serializer para actualizar tipo CIE individual"""

    tipo_cie = serializers.ChoiceField(
        choices=DiagnosticoCIEHistorial.TipoCIE.choices,
        required=True
    )

    def validate(self, data):
        if not self.instance:
            raise serializers.ValidationError("Instancia requerida para actualización")
        return data


class DiagnosticoCIECodigoPersonalizadoSerializer(serializers.Serializer):
    """
    Serializer para actualizar el código CIE-10 personalizado de un diagnóstico.
    Solo disponible mientras el historial está en estado BORRADOR.

    - Enviar un código válido (ej. K08.1) → se guarda como personalizado.
    - Enviar null o cadena vacía → se restaura el código del catálogo.
    """

    codigo_cie_personalizado = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        required=True,
        max_length=20,
        help_text=(
            'Código CIE-10 personalizado (ej. K08.1). '
            'Envíe null o cadena vacía para usar el código del catálogo.'
        )
    )

    def validate_codigo_cie_personalizado(self, value):
        if value is None or value.strip() == '':
            return ''  # señal de "restaurar catálogo"
        return validar_formato_cie10(value)


class SincronizarDiagnosticosSerializer(serializers.Serializer):
    """Serializer para sincronización de diagnósticos"""

    diagnosticos_finales = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        help_text="Lista de diagnósticos que deben permanecer en el historial"
    )

    tipo_carga = serializers.ChoiceField(
        choices=[
            ('nuevos', 'Solo nuevos diagnósticos'),
            ('todos', 'Todos los diagnósticos del snapshot'),
        ],
        required=True
    )

    def validate_diagnosticos_finales(self, value):
        for diag in value:
            if not diag.get('diagnostico_dental_id'):
                raise serializers.ValidationError(
                    "Cada diagnóstico debe tener 'diagnostico_dental_id'"
                )
            if not diag.get('tipo_cie'):
                raise serializers.ValidationError(
                    "Cada diagnóstico debe tener 'tipo_cie' (PRE/DEF)"
                )
            # Validar código personalizado si se envía
            codigo = diag.get('codigo_cie_personalizado')
            if codigo and codigo.strip():
                try:
                    validar_formato_cie10(codigo)
                except serializers.ValidationError as exc:
                    raise serializers.ValidationError(
                        f"diagnostico_dental_id {diag.get('diagnostico_dental_id')}: {exc.detail}"
                    )
        return value