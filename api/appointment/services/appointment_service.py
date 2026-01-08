# api/appointment/services/appointment_service.py
import logging
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from ..models import Cita, HorarioAtencion, EstadoCita
from ..repositories import CitaRepository, HorarioAtencionRepository, RecordatorioCitaRepository


class CitaService:
    """Servicio con lógica de negocio para citas"""
    
    @staticmethod
    def obtener_todas_citas(filtros=None):
        """Obtiene todas las citas con filtros opcionales"""
        return CitaRepository.obtener_todas(filtros)
    
    @staticmethod
    def obtener_cita_por_id(cita_id):
        """Obtiene una cita por ID"""
        return CitaRepository.obtener_por_id(cita_id)
    
    @staticmethod
    def obtener_citas_por_fecha_y_odontologo(fecha, odontologo_id):
        """Obtiene las citas de un odontólogo en una fecha"""
        return CitaRepository.obtener_por_fecha_y_odontologo(fecha, odontologo_id)
    
    @staticmethod
    def obtener_citas_por_semana(fecha_inicio, odontologo_id=None):
        """Obtiene citas de una semana"""
        return CitaRepository.obtener_por_semana(fecha_inicio, odontologo_id)
    
    @staticmethod
    def obtener_citas_por_paciente(paciente_id):
        """Obtiene todas las citas de un paciente"""
        return CitaRepository.obtener_por_paciente(paciente_id)
    
    @staticmethod
    @transaction.atomic
    def crear_cita(data):
        """Crea una nueva cita con validaciones"""
        # Calcular hora_fin
        hora_inicio_dt = datetime.combine(datetime.today(), data['hora_inicio'])
        hora_fin_dt = hora_inicio_dt + timedelta(minutes=data['duracion'])
        data['hora_fin'] = hora_fin_dt.time()
        
        # Verificar disponibilidad
        disponible, cita_conflicto = CitaRepository.verificar_disponibilidad(
            data['odontologo'].id,
            data['fecha'],
            data['hora_inicio'],
            data['hora_fin']
        )
        
        if not disponible:
            raise ValidationError(
                f"El odontólogo ya tiene una cita de {cita_conflicto.hora_inicio} a {cita_conflicto.hora_fin}"
            )
        
        # Crear la cita
        cita = CitaRepository.crear(data)
        return cita
    
    @staticmethod
    @transaction.atomic
    def actualizar_cita(cita_id, data):
        """Actualiza una cita existente"""
        cita = CitaRepository.obtener_por_id(cita_id)
        
        if not cita:
            raise ValidationError("Cita no encontrada")
        
        if not cita.puede_ser_cancelada:
            raise ValidationError("Esta cita no puede ser modificada")
        
        # Si se cambia la fecha u hora, verificar disponibilidad
        if 'fecha' in data or 'hora_inicio' in data or 'duracion' in data:
            fecha = data.get('fecha', cita.fecha)
            hora_inicio = data.get('hora_inicio', cita.hora_inicio)
            duracion = data.get('duracion', cita.duracion)
            
            hora_inicio_dt = datetime.combine(datetime.today(), hora_inicio)
            hora_fin_dt = hora_inicio_dt + timedelta(minutes=duracion)
            hora_fin = hora_fin_dt.time()
            
            odontologo_id = data.get('odontologo', cita.odontologo).id
            
            disponible, cita_conflicto = CitaRepository.verificar_disponibilidad(
                odontologo_id,
                fecha,
                hora_inicio,
                hora_fin,
                excluir_cita_id=cita_id
            )
            
            if not disponible:
                raise ValidationError(
                    f"El odontólogo ya tiene una cita de {cita_conflicto.hora_inicio} a {cita_conflicto.hora_fin}"
                )
            
            data['hora_fin'] = hora_fin
        
        return CitaRepository.actualizar(cita, data)
    
    @staticmethod
    @transaction.atomic
    def cancelar_cita(cita_id, motivo, usuario):
        """Cancela una cita"""
        cita = CitaRepository.obtener_por_id(cita_id)
        
        if not cita:
            raise ValidationError("Cita no encontrada")
        
        # ✅ MEJORA: Loggear el estado actual para diagnóstico
        logger = logging.getLogger(__name__)
        logger.info(f"Intentando cancelar cita {cita_id} con estado actual: {cita.estado}")
        
        # ✅ CORRECCIÓN: Usar la propiedad del modelo directamente
        if not cita.puede_ser_cancelada:
            raise ValidationError(
                f"Esta cita no puede ser cancelada (estado actual: {cita.estado})"
            )
        
        data = {
            'estado': EstadoCita.CANCELADA,
            'motivo_cancelacion': motivo,
            'fecha_cancelacion': timezone.now(),
            'cancelada_por': usuario
        }
        
        return CitaRepository.actualizar(cita, data)
    
    @staticmethod
    @transaction.atomic
    def reprogramar_cita(cita_id, nueva_fecha, nueva_hora_inicio, usuario):
        """Reprograma una cita creando una nueva"""
        cita = CitaRepository.obtener_por_id(cita_id)
        
        if not cita:
            raise ValidationError("Cita no encontrada")
        
        if not cita.puede_ser_cancelada:
            raise ValidationError("Esta cita no puede ser reprogramada")
        
        # Calcular hora_fin para nueva cita
        hora_inicio_dt = datetime.combine(datetime.today(), nueva_hora_inicio)
        hora_fin_dt = hora_inicio_dt + timedelta(minutes=cita.duracion)
        hora_fin = hora_fin_dt.time()
        
        # Verificar disponibilidad (excluir la cita original si tiene el mismo día/hora)
        disponible, cita_conflicto = CitaRepository.verificar_disponibilidad(
            cita.odontologo.id,
            nueva_fecha,
            nueva_hora_inicio,
            hora_fin,
            excluir_cita_id=cita_id
        )
        
        if not disponible:
            raise ValidationError(
                f"El odontólogo ya tiene una cita de {cita_conflicto.hora_inicio} a {cita_conflicto.hora_fin}"
            )
        
        # ✅ CORRECCIÓN CRÍTICA: Marcar cita actual como reprogramada y desactivarla
        CitaRepository.actualizar(cita, {
            'estado': EstadoCita.REPROGRAMADA,
            'activo': False  # Desactivar la cita original
        })
        
        # ✅ CORRECCIÓN CRÍTICA: Crear nueva cita con estado REPROGRAMADA (no PROGRAMADA)
        nueva_cita_data = {
            'paciente': cita.paciente,
            'odontologo': cita.odontologo,
            'fecha': nueva_fecha,
            'hora_inicio': nueva_hora_inicio,
            'hora_fin': hora_fin,
            'duracion': cita.duracion,
            'tipo_consulta': cita.tipo_consulta,
            'motivo_consulta': cita.motivo_consulta,
            'observaciones': f"Reprogramada desde {cita.fecha} {cita.hora_inicio}. {cita.observaciones}",
            'cita_original': cita,
            'estado': EstadoCita.REPROGRAMADA,  # ✅ CAMBIO AQUÍ: Estado REPROGRAMADA
            'activo': True
        }
        
        nueva_cita = CitaRepository.crear(nueva_cita_data)
        
        # ✅ Asegurar que el estado display sea correcto
        nueva_cita.estado = EstadoCita.REPROGRAMADA
        nueva_cita.save()
        
        return nueva_cita
    
    @staticmethod
    @transaction.atomic
    def cambiar_estado_cita(cita_id, nuevo_estado):
        """Cambia el estado de una cita"""
        cita = CitaRepository.obtener_por_id(cita_id)
        
        if not cita:
            raise ValidationError("Cita no encontrada")
        
        data = {'estado': nuevo_estado}
        
        if nuevo_estado == EstadoCita.ASISTIDA:
            data['fecha_atencion'] = timezone.now()
        
        return CitaRepository.actualizar(cita, data)
    
    @staticmethod
    def obtener_horarios_disponibles(odontologo_id, fecha, duracion=30):
        """Obtiene horarios disponibles para un odontólogo en una fecha"""
        dia_semana = fecha.weekday()
        
        # Obtener horarios de atención
        horarios = HorarioAtencionRepository.obtener_por_odontologo_y_dia(
            odontologo_id, dia_semana
        )
        
        if not horarios:
            return []
        
        # Obtener citas ya programadas (solo activas)
        citas_programadas = CitaRepository.obtener_por_fecha_y_odontologo(
            fecha, odontologo_id
        ).filter(activo=True)
        
        horarios_disponibles = []
        
        for horario in horarios:
            hora_actual = horario.hora_inicio
            
            while hora_actual < horario.hora_fin:
                hora_actual_dt = datetime.combine(datetime.today(), hora_actual)
                hora_fin_dt = hora_actual_dt + timedelta(minutes=duracion)
                hora_fin = hora_fin_dt.time()
                
                if hora_fin > horario.hora_fin:
                    break
                
                # Verificar conflictos
                hay_conflicto = False
                for cita in citas_programadas:
                    if (hora_actual < cita.hora_fin and hora_fin > cita.hora_inicio):
                        hay_conflicto = True
                        break
                
                if not hay_conflicto:
                    horarios_disponibles.append({
                        'hora_inicio': hora_actual.strftime('%H:%M'),
                        'hora_fin': hora_fin.strftime('%H:%M')
                    })
                
                hora_actual_dt = hora_actual_dt + timedelta(minutes=duracion)
                hora_actual = hora_actual_dt.time()
        
        return horarios_disponibles
    
    @staticmethod
    def eliminar_cita(cita_id):
        """Elimina lógicamente una cita"""
        cita = CitaRepository.obtener_por_id(cita_id)
        
        if not cita:
            raise ValidationError("Cita no encontrada")
        
        return CitaRepository.eliminar_logico(cita)


class HorarioAtencionService:
    """Servicio para horarios de atención"""
    
    @staticmethod
    def obtener_horarios_por_odontologo(odontologo_id):
        """Obtiene todos los horarios de un odontólogo"""
        return HorarioAtencionRepository.obtener_todos_por_odontologo(odontologo_id)
    
    @staticmethod
    def obtener_horario_por_id(horario_id):
        """Obtiene un horario por ID"""
        return HorarioAtencionRepository.obtener_por_id(horario_id)
    
    @staticmethod
    @transaction.atomic
    def crear_horario(data):
        """Crea un nuevo horario de atención"""
        return HorarioAtencionRepository.crear(data)
    
    @staticmethod
    @transaction.atomic
    def actualizar_horario(horario_id, data):
        """Actualiza un horario existente"""
        horario = HorarioAtencionRepository.obtener_por_id(horario_id)
        
        if not horario:
            raise ValidationError("Horario no encontrado")
        
        return HorarioAtencionRepository.actualizar(horario, data)
    
    @staticmethod
    @transaction.atomic
    def eliminar_horario(horario_id):
        """Elimina lógicamente un horario"""
        horario = HorarioAtencionRepository.obtener_por_id(horario_id)
        
        if not horario:
            raise ValidationError("Horario no encontrado")
        
        return HorarioAtencionRepository.eliminar_logico(horario)


class RecordatorioService:
    """Servicio para gestión de recordatorios"""
    
    @staticmethod
    @transaction.atomic
    def crear_recordatorio(cita, tipo_recordatorio, mensaje):
        """Crea un recordatorio para una cita"""
        data = {
            'cita': cita,
            'tipo_recordatorio': tipo_recordatorio,
            'mensaje': mensaje,
            'enviado_exitosamente': False
        }
        
        return RecordatorioCitaRepository.crear(data)
    
    @staticmethod
    def obtener_recordatorios_por_cita(cita_id):
        """Obtiene todos los recordatorios de una cita"""
        return RecordatorioCitaRepository.obtener_por_cita(cita_id)