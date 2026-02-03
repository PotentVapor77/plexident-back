# api/clinical_records/utils.py

from django.db.models import Max
from django.utils import timezone
import uuid
import hashlib
import time


class ClinicalRecordNumberGenerator:
    """
    Clase para generar números automáticos para historiales clínicos
    """
    
    @staticmethod
    def generar_numero_historia_clinica_unica():
        """
        Genera número de historia clínica única garantizando unicidad.
        Formato: HC-{YYYY}{SECUENCIA}
        Ejemplo: HC-2026000001
        Longitud: ~15 caracteres
        """
        from api.clinical_records.models import ClinicalRecord
        from django.db import transaction
        
        año_actual = timezone.now().year
        
        # Obtener el último número del año actual con transacción atómica
        with transaction.atomic():
            # Bloquear la tabla para evitar duplicados en entornos concurrentes
            ClinicalRecord.objects.select_for_update().filter(
                numero_historia_clinica_unica__startswith=f'HC-{año_actual}'
            ).exists()
            
            ultimo_numero = ClinicalRecord.objects.filter(
                numero_historia_clinica_unica__startswith=f'HC-{año_actual}'
            ).order_by('-numero_historia_clinica_unica').first()
            
            if ultimo_numero:
                # Extraer la secuencia numérica
                try:
                    secuencia = int(ultimo_numero.numero_historia_clinica_unica.split('-')[1][4:]) + 1
                except (IndexError, ValueError):
                    secuencia = 1
            else:
                secuencia = 1
        
        return f'HC-{año_actual}{secuencia:05d}'
    
    @staticmethod
    def generar_numero_archivo(paciente_id):
        """
        Genera número de archivo único por historial clínico OPTIMIZADO.
        Formato: AR-{6HASH}-{TIMESTAMP}
        Ejemplo: AR-A1B2C3-260125-1530
        Longitud máxima: 22 caracteres (deja espacio para extensiones futuras)
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            String con número de archivo único y corto
        """
        # Hash corto de 6 caracteres del UUID del paciente
        paciente_hash = hashlib.md5(
            str(paciente_id).encode()
        ).hexdigest()[:6].upper()
        
        # Timestamp compacto: YYMMDD-HHMM (11 caracteres)
        timestamp = timezone.now().strftime('%y%m%d-%H%M')
        
        # Formato: AR-{6chars}-{11chars} = 3 + 6 + 1 + 11 = 21 caracteres
        return f'AR-{paciente_hash}-{timestamp}'
    
    @staticmethod
    def generar_numero_hoja(paciente_id):
        """
        Genera el número de hoja basado en historiales existentes del paciente.
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            Número de hoja (incrementa con cada historial)
        """
        from api.clinical_records.models import ClinicalRecord
        
        count = ClinicalRecord.objects.filter(
            paciente_id=paciente_id,
            activo=True
        ).count()
        
        return count + 1
    