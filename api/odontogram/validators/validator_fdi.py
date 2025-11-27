from django.forms import ValidationError

from api.odontogram.constants import FDIConstants


def validar_codigo_fdi(codigo_fdi):
    """Valida que código FDI sea válido (11-48, 51-85)"""
    codigo_fdi = codigo_fdi.strip() if codigo_fdi else "" 
     
    if not codigo_fdi or len(codigo_fdi) != 2:
        raise ValidationError("El código FDI debe tener exactamente 2 dígitos")
    
    if not codigo_fdi.isdigit():
        raise ValidationError("El código FDI debe contener solo dígitos")
    
    info = FDIConstants.obtener_info_fdi(codigo_fdi)
    if not info:
        raise ValidationError(f"'{codigo_fdi}' no es un código FDI válido")
