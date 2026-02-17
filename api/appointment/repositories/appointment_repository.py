# api/appointment/repositories/appointment_repository.py
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from ..models import Cita, HorarioAtencion, RecordatorioCita, EstadoCita


class CitaRepository:
    """Repositorio para operaciones de base de datos de Citas"""
    
    @staticmethod
    def obtener_todas(filtros=None):
        """Obtiene todas las citas con filtros opcionales"""
        queryset = Cita.objects.select_related(
            'paciente', 'odontologo', 'creado_por', 'cancelada_por'
        ).filter(activo=True)
        
        if filtros:
            if 'odontologo' in filtros:
                queryset = queryset.filter(odontologo_id=filtros['odontologo'])
            
            if 'paciente' in filtros:
                queryset = queryset.filter(paciente_id=filtros['paciente'])
            
            if 'fecha' in filtros:
                queryset = queryset.filter(fecha=filtros['fecha'])
            
            if 'fecha_inicio' in filtros and 'fecha_fin' in filtros:
                queryset = queryset.filter(
                    fecha__range=[filtros['fecha_inicio'], filtros['fecha_fin']]
                )
            
            if 'estado' in filtros:
                queryset = queryset.filter(estado=filtros['estado'])
            
            if 'tipo_consulta' in filtros:
                queryset = queryset.filter(tipo_consulta=filtros['tipo_consulta'])
        
        return queryset.order_by('fecha', 'hora_inicio')
    
    @staticmethod
    def obtener_por_id(cita_id):
        """Obtiene una cita por ID"""
        try:
            return Cita.objects.select_related(
                'paciente', 'odontologo', 'creado_por',
                'cancelada_por', 'cita_original'
            ).get(id=cita_id, activo=True)
        except Cita.DoesNotExist:
            return None
    
    @staticmethod
    def obtener_por_fecha_y_odontologo(fecha, odontologo_id):
        """Obtiene citas de un odontólogo en una fecha específica"""
        return Cita.objects.select_related('paciente', 'odontologo').filter(
            fecha=fecha,
            odontologo_id=odontologo_id,
            activo=True
        ).exclude(
            estado__in=[EstadoCita.CANCELADA, EstadoCita.REPROGRAMADA]
        ).order_by('hora_inicio')
    
    @staticmethod
    def obtener_por_semana(fecha_inicio, odontologo_id=None):
        """Obtiene citas de una semana"""
        fecha_fin = fecha_inicio + timedelta(days=6)
        queryset = Cita.objects.select_related('paciente', 'odontologo').filter(
            fecha__range=[fecha_inicio, fecha_fin],
            activo=True
        ).exclude(
            estado__in=[EstadoCita.CANCELADA, EstadoCita.REPROGRAMADA]
        )
        
        if odontologo_id:
            queryset = queryset.filter(odontologo_id=odontologo_id)
        
        return queryset.order_by('fecha', 'hora_inicio')
    
    @staticmethod
    def obtener_por_paciente(paciente_id):
        """Obtiene todas las citas de un paciente"""
        return Cita.objects.select_related('odontologo').filter(
            paciente_id=paciente_id,
            activo=True
        ).order_by('-fecha', '-hora_inicio')
    
    @staticmethod
    def crear(data):
        """Crea una nueva cita"""
        return Cita.objects.create(**data)
    
    @staticmethod
    def actualizar(cita, data):
        """Actualiza una cita existente"""
        for key, value in data.items():
            setattr(cita, key, value)
        cita.save()
        return cita
    
    @staticmethod
    def eliminar_logico(cita):
        """Elimina lógicamente una cita"""
        cita.activo = False
        cita.save()
        return cita
    
    @staticmethod
    def verificar_disponibilidad(odontologo_id, fecha, hora_inicio, hora_fin, excluir_cita_id=None):
        """Verifica si un odontólogo está disponible en un horario"""
        queryset = Cita.objects.filter(
            odontologo_id=odontologo_id,
            fecha=fecha,
            activo=True
        ).exclude(
            estado__in=[EstadoCita.CANCELADA, EstadoCita.REPROGRAMADA]
        )
        
        if excluir_cita_id:
            queryset = queryset.exclude(id=excluir_cita_id)
        
        # Verificar solapamiento de horarios
        for cita in queryset:
            if (hora_inicio < cita.hora_fin and hora_fin > cita.hora_inicio):
                return False, cita
        
        return True, None
    
    @staticmethod
    def obtener_citas_pendientes_recordatorio():
        """
        Obtiene citas que requieren recordatorio (24 horas antes).
        Busca citas cuya fecha/hora esté entre 23 y 25 horas en el futuro.
        """
        ahora = timezone.now()
        limite_inferior = ahora + timedelta(hours=23)
        limite_superior = ahora + timedelta(hours=25)
        return Cita.objects.filter(
            activo=True,
            recordatorio_enviado=False, #
            estado__in=[EstadoCita.PROGRAMADA, EstadoCita.CONFIRMADA]
        ).filter(
            fecha__gte=limite_inferior.date(),
            fecha__lte=limite_superior.date()
        ).select_related('paciente', 'odontologo')



class HorarioAtencionRepository:
    """Repositorio para horarios de atención"""
    
    @staticmethod
    def obtener_por_odontologo_y_dia(odontologo_id, dia_semana):
        """Obtiene horarios de un odontólogo para un día específico"""
        return HorarioAtencion.objects.filter(
            odontologo_id=odontologo_id,
            dia_semana=dia_semana,
            activo=True
        ).order_by('hora_inicio')
    
    @staticmethod
    def obtener_todos_por_odontologo(odontologo_id):
        """Obtiene todos los horarios de un odontólogo"""
        return HorarioAtencion.objects.filter(
            odontologo_id=odontologo_id,
            activo=True
        ).order_by('dia_semana', 'hora_inicio')
    
    @staticmethod
    def obtener_por_id(horario_id):
        """Obtiene un horario por ID"""
        try:
            return HorarioAtencion.objects.get(id=horario_id, activo=True)
        except HorarioAtencion.DoesNotExist:
            return None
    
    @staticmethod
    def crear(data):
        """Crea un nuevo horario de atención"""
        return HorarioAtencion.objects.create(**data)
    
    @staticmethod
    def actualizar(horario, data):
        """Actualiza un horario existente"""
        for key, value in data.items():
            setattr(horario, key, value)
        horario.save()
        return horario
    
    @staticmethod
    def eliminar_logico(horario):
        """Elimina lógicamente un horario"""
        horario.activo = False
        horario.save()
        return horario


class RecordatorioCitaRepository:
    """Repositorio para recordatorios"""
    
    @staticmethod
    def crear(data):
        """Crea un nuevo recordatorio"""
        return RecordatorioCita.objects.create(**data)
    
    @staticmethod
    def obtener_por_cita(cita_id):
        """Obtiene todos los recordatorios de una cita"""
        return RecordatorioCita.objects.filter(
            cita_id=cita_id
        ).order_by('-fecha_envio')
    
    @staticmethod
    def obtener_por_id(recordatorio_id):
        """Obtiene un recordatorio por ID"""
        try:
            return RecordatorioCita.objects.get(id=recordatorio_id)
        except RecordatorioCita.DoesNotExist:
            return None

