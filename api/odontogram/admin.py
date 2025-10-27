
# api/odontogram/admin.py
from django.contrib import admin
from .models import (
    CategoriaDiagnostico,
    Diagnostico,
    AreaAfectada,
    DiagnosticoAreaAfectada,
    TipoAtributoClinico,
    OpcionAtributoClinico,
    DiagnosticoAtributoClinico,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma
)

# Registro básico (mostrar en admin)
admin.site.register(CategoriaDiagnostico)
admin.site.register(Diagnostico)
admin.site.register(AreaAfectada)
admin.site.register(DiagnosticoAreaAfectada)
admin.site.register(TipoAtributoClinico)
admin.site.register(OpcionAtributoClinico)
admin.site.register(DiagnosticoAtributoClinico)
admin.site.register(Diente)
admin.site.register(SuperficieDental)
admin.site.register(DiagnosticoDental)
admin.site.register(HistorialOdontograma)