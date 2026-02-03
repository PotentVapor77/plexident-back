# api/clinical_records/services/number_generator_service.py
"""
Servicio para generación de números únicos de historiales clínicos
"""
import hashlib
from django.utils import timezone
from api.clinical_records.models import ClinicalRecord


class NumberGeneratorService:
    """Servicio para generar números únicos y optimizados"""
    
    @staticmethod
    def generar_numero_archivo(paciente_id):
        """
        Genera número de archivo optimizado para no exceder 50 caracteres
        Formato: PAC-{HASH6}-{TIMESTAMP}
        Ejemplo: PAC-a1b2c3-260125-1530
        Total: ~22 caracteres
        """
        # Hash de 6 caracteres del UUID del paciente
        hash_paciente = hashlib.md5(
            str(paciente_id).encode()
        ).hexdigest()[:6]
        
        # Timestamp compacto (YYMMDD-HHMM = 11 chars)
        timestamp = timezone.now().strftime('%y%m%d-%H%M')
        
        # PAC-{6chars}-{11chars} = 22 caracteres
        return f"PAC-{hash_paciente}-{timestamp}"
    
    @staticmethod
    def generar_numero_archivo_con_fecha(numero_base):
        """
        Genera variación del número de archivo con fecha adicional
        Usado cuando ya existe un historial activo
        Formato: {NUMERO_BASE}-{DATE}
        """
        import random
        sufijo = random.randint(1, 999)
        nuevo_numero = f"{numero_base}-{sufijo:03d}"
        
        # Validar longitud
        if len(nuevo_numero) > 50:
            max_base_length = 50 - 4  # 4 = guion + 3 dígitos
            nuevo_numero = f"{numero_base[:max_base_length]}-{sufijo:03d}"
        
        return nuevo_numero
    
    @staticmethod
    def generar_numero_historia_clinica_unica():
        """
        Genera número de historia clínica única
        Formato: HCU-{TIMESTAMP}-{RANDOM}
        Ejemplo: HCU-20260125-a1b2c3
        Total: ~21 caracteres
        """
        timestamp = timezone.now().strftime('%Y%m%d')
        
        # Generar hash aleatorio corto
        random_hash = hashlib.md5(
            f"{timestamp}{timezone.now().microsecond}".encode()
        ).hexdigest()[:6]
        
        return f"HCU-{timestamp}-{random_hash}"
    
    @staticmethod
    def generar_numero_hoja(paciente_id):
        """
        Genera número de hoja basado en historiales existentes
        """
        count = ClinicalRecord.objects.filter(
            paciente_id=paciente_id,
            activo=True
        ).count()
        
        return count + 1
    
    
    @staticmethod
    def obtener_numero_archivo_existente(paciente_id):
        """
        NOTA: Ya no es necesario reutilizar números de archivo.
        Cada historial debe tener su propio número único generado
        con generar_numero_archivo() que incluye timestamp.
        """
        
        return None
