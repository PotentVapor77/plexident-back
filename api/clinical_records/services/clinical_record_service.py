"""
Servicio principal para lógica de negocio de Historiales Clínicos
"""
import logging
from django.utils import timezone
from django.core.exceptions import ValidationError

from api.clinical_records.repositories import ClinicalRecordRepository
from api.clinical_records.models import ClinicalRecord
from api.patients.models.paciente import Paciente
from api.clinical_records.config import INSTITUCION_CONFIG
from api.clinical_records.services.form033_storage_service import Form033StorageService
from api.clinical_records.services.indicadores_service import ClinicalRecordIndicadoresService

from typing import Optional, Dict, Any
from .number_generator_service import NumberGeneratorService
from .vital_signs_service import VitalSignsService
from .record_loader_service import RecordLoaderService

logger = logging.getLogger(__name__)


class ClinicalRecordService:
    """Servicio para la lógica de negocio de Historiales Clínicos"""
    
    @classmethod
    def crear_historial(cls, data):
        """
        Crea un nuevo historial clínico con datos pre-cargados
        """
        paciente = data.get('paciente')
        paciente_id = paciente.id
        
        # === GENERAR NÚMEROS ÚNICOS ===
        numero_historia_unica = (
            NumberGeneratorService.generar_numero_historia_clinica_unica()
        )
        numero_archivo = NumberGeneratorService.generar_numero_archivo(
            paciente_id
        )
        
        # Validar longitud antes de continuar
        if len(numero_archivo) > 50:
            raise ValidationError({
                'numero_archivo': (
                    f'Número de archivo muy largo: {len(numero_archivo)} caracteres. '
                    f'Máximo permitido: 50'
                )
            })
        
        if len(numero_historia_unica) > 50:
            raise ValidationError({
                'numero_historia_clinica_unica': (
                    f'Número de historia clínica muy largo: {len(numero_historia_unica)} caracteres. '
                    f'Máximo permitido: 50'
                )
            })
        
        
        # Asignar números generados
        data['numero_historia_clinica_unica'] = numero_historia_unica
        data['numero_archivo'] = numero_archivo
        data['numero_hoja'] = NumberGeneratorService.generar_numero_hoja(paciente_id)
        
        # === DATOS POR DEFECTO ===
        if not data.get('establecimiento_salud'):
            data['establecimiento_salud'] = INSTITUCION_CONFIG['ESTABLECIMIENTO_SALUD']
        
        if not data.get('institucion_sistema'):
            data['institucion_sistema'] = INSTITUCION_CONFIG['INSTITUCION_SISTEMA']
            
        if not data.get('unicodigo'):
            data['unicodigo'] = INSTITUCION_CONFIG['UNICODIGO_DEFAULT']
        
        if not data.get('embarazada'):
            data['embarazada'] = paciente.embarazada
        
        # === CARGAR DATOS PREVIOS DEL PACIENTE ===
        ultimos_datos = ClinicalRecordRepository.obtener_ultimos_datos_paciente(
            paciente_id
        )
        
        # === MANEJAR CONSTANTES VITALES ===
        constantes_vitales_nuevas = False
        motivo_consulta_nuevo = False
        enfermedad_actual_nueva = False
        
        if VitalSignsService.tiene_datos_vitales(data):
            # Crear nuevas constantes vitales
            nueva_constante = VitalSignsService.crear_constantes_vitales(
                paciente=paciente,
                data=data,
                creado_por=data.get('creado_por')
            )
            data['constantes_vitales'] = nueva_constante
            constantes_vitales_nuevas = True
            
            if data.get('motivo_consulta'):
                motivo_consulta_nuevo = True
            if data.get('enfermedad_actual'):
                enfermedad_actual_nueva = True
        else:
            # Usar última constante vital existente
            ultima_constante = VitalSignsService.obtener_ultima_constante(paciente_id)
            if ultima_constante:
                data['constantes_vitales'] = ultima_constante
                
                # Extraer los datos de texto antes de limpiarlos
                motivo_consulta = data.get('motivo_consulta')
                enfermedad_actual = data.get('enfermedad_actual')
                
                # Actualizar motivo/enfermedad si se proporcionan
                if VitalSignsService.tiene_datos_texto(data):
                    # Actualizar la constante vital existente
                    VitalSignsService.actualizar_constantes_existentes(
                        ultima_constante,
                        data
                    )
                    
                    # Asignar los valores actualizados al historial
                    if motivo_consulta:
                        data['motivo_consulta'] = motivo_consulta
                        motivo_consulta_nuevo = True
                    if enfermedad_actual:
                        data['enfermedad_actual'] = enfermedad_actual
                        enfermedad_actual_nueva = True
        
        # === PRE-CARGAR OTRAS SECCIONES ===
        secciones = [
            'antecedentes_personales',
            'antecedentes_familiares',
            'examen_estomatognatico',
            'indices_caries'
        ]
        for seccion in secciones:
            if not data.get(seccion) and ultimos_datos.get(seccion):
                data[seccion] = ultimos_datos[seccion]
        if not data.get('indicadores_salud_bucal'):
            print(f"\n{'='*60}")
            print(f"BUSCANDO INDICADORES PARA ASOCIAR AL NUEVO HISTORIAL")
            print(f"Paciente ID: {paciente_id}")
        indicadores = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(
            str(paciente_id)
        )
        
        if indicadores:
            data['indicadores_salud_bucal'] = indicadores
            print(f" Indicadores encontrados y listos para asociar:")
            print(f"   - ID: {indicadores.id}")
            print(f"   - Fecha: {indicadores.fecha}")
        else:
            print(f" No hay indicadores previos para este paciente")
        
        print(f"{'='*60}\n")
        
        # === LIMPIEZA DE DATOS ===
        # Remover campos que no pertenecen al modelo ClinicalRecord
        motivo_consulta_valor = data.get('motivo_consulta')
        enfermedad_actual_valor = data.get('enfermedad_actual')
        VitalSignsService.limpiar_campos_del_dict(data)
        
        # Restaurar los valores de texto si existen
        if motivo_consulta_valor is not None:
            data['motivo_consulta'] = motivo_consulta_valor
        if enfermedad_actual_valor is not None:
            data['enfermedad_actual'] = enfermedad_actual_valor
        
        # Asignar flags
        data['constantes_vitales_nuevas'] = constantes_vitales_nuevas
        data['motivo_consulta_nuevo'] = motivo_consulta_nuevo
        data['enfermedad_actual_nueva'] = enfermedad_actual_nueva
        
        # === CREAR HISTORIAL ===
        historial = ClinicalRecord(**data)
        historial.full_clean()
        historial.save()
        
        logger.info(
            f"Historial creado: {numero_historia_unica} "
            f"para paciente {paciente.nombre_completo}"
        )
        
        return historial
    
    @classmethod
    def actualizar_historial(cls, historial_id, data):
        """
        Actualiza un historial clínico existente
        Crea nuevos registros si se envían datos editables
        
        Args:
            historial_id: UUID del historial
            data: Diccionario con datos a actualizar
            
        Returns:
            Instancia de ClinicalRecord actualizada
        """
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        
        # Validar estado
        if historial.estado == 'CERRADO':
            raise ValidationError('No se puede editar un historial cerrado.')
        
        # Eliminar campos prohibidos
        campos_prohibidos = [
            'numero_historia_clinica_unica',
            'numero_archivo',
            'numero_hoja',
            'paciente',
            'fecha_atencion',
            'fecha_cierre'
        ]
        for campo in campos_prohibidos:
            data.pop(campo, None)
        
        # Flags de actualización
        actualizo_constantes = False
        actualizo_motivo = False
        actualizo_enfermedad = False
        
        # === MANEJAR CONSTANTES VITALES ===
        tiene_datos_vitales = VitalSignsService.tiene_datos_vitales(data)
        tiene_datos_texto = VitalSignsService.tiene_datos_texto(data)
        
        if tiene_datos_vitales or tiene_datos_texto:
            constante_actual = historial.constantes_vitales
            
            # Preparar datos para nueva constante vital
            constante_vital_data = {
                'paciente': historial.paciente,
                'temperatura': data.get(
                    'temperatura',
                    constante_actual.temperatura if constante_actual else None
                ),
                'pulso': data.get(
                    'pulso',
                    constante_actual.pulso if constante_actual else None
                ),
                'frecuencia_respiratoria': data.get(
                    'frecuencia_respiratoria',
                    constante_actual.frecuencia_respiratoria if constante_actual else None
                ),
                'presion_arterial': data.get(
                    'presion_arterial',
                    constante_actual.presion_arterial if constante_actual else ''
                ),
                'motivo_consulta': data.get(
                    'motivo_consulta',
                    constante_actual.motivo_consulta if constante_actual else ''
                ),
                'enfermedad_actual': data.get(
                    'enfermedad_actual',
                    constante_actual.enfermedad_actual if constante_actual else ''
                ),
                'creado_por': data.get('creado_por', historial.creado_por),
            }
            
            # Crear nueva constante vital
            nueva_constante = VitalSignsService.crear_constantes_vitales(
                paciente=historial.paciente,
                data=constante_vital_data,
                creado_por=constante_vital_data['creado_por']
            )
            
            # Asociar al historial
            historial.constantes_vitales = nueva_constante
            historial.constantes_vitales_nuevas = True
            actualizo_constantes = True
            
            # Actualizar flags de texto
            if data.get('motivo_consulta') is not None:
                historial.motivo_consulta = data['motivo_consulta']
                historial.motivo_consulta_nuevo = True
                actualizo_motivo = True
            
            if data.get('enfermedad_actual') is not None:
                historial.enfermedad_actual = data['enfermedad_actual']
                historial.enfermedad_actual_nueva = True
                actualizo_enfermedad = True
        
        # Limpiar campos de constantes vitales del diccionario
        VitalSignsService.limpiar_campos_del_dict(data)
        
        # === ACTUALIZAR CAMPOS DIRECTOS ===
        campos_permitidos = [
            'motivo_consulta', 'embarazada', 'enfermedad_actual',
            'observaciones', 'estado', 'odontologo_responsable',
            'unicodigo', 'establecimiento_salud', 'numero_hoja',
            'institucion_sistema', 'antecedentes_personales',
            'antecedentes_familiares', 'examen_estomatognatico'
        ]
        
        for key, value in data.items():
            if key in campos_permitidos and hasattr(historial, key):
                setattr(historial, key, value)
                
                # Marcar flags si no se marcaron antes
                if key == 'motivo_consulta' and not actualizo_motivo:
                    historial.motivo_consulta_nuevo = True
                if key == 'enfermedad_actual' and not actualizo_enfermedad:
                    historial.enfermedad_actual_nueva = True
        
        # === VALIDACIONES ADICIONALES ===
        cls._validar_datos_historial(historial)
        
        # Guardar cambios
        historial.full_clean()
        historial.save()
        
        logger.info(
            f"Historial {historial_id} actualizado: "
            f"constantes={actualizo_constantes}, "
            f"motivo={actualizo_motivo}, "
            f"enfermedad={actualizo_enfermedad}"
        )
        
        return historial
    
    @staticmethod
    def _validar_datos_historial(historial):
        """Validaciones de negocio del historial"""
        # Validar embarazo según sexo
        if historial.embarazada == 'SI' and historial.paciente.sexo == 'M':
            raise ValidationError(
                'Un paciente masculino no puede estar embarazado.'
            )
        
        # Validar rol del odontólogo
        if (historial.odontologo_responsable and 
            historial.odontologo_responsable.rol != 'Odontologo'):
            raise ValidationError('El responsable debe ser un odontólogo.')
        
        # Validar cambio de estado desde CERRADO
        if historial.pk:
            old_instance = ClinicalRecord.objects.get(pk=historial.pk)
            if (old_instance.estado == 'CERRADO' and 
                historial.estado != 'CERRADO'):
                raise ValidationError(
                    'No se puede cambiar el estado de un historial cerrado. '
                    'Use reabrir_historial.'
                )
    
    @staticmethod
    def cerrar_historial(historial_id, usuario):
        """
        Cierra un historial clínico, impidiendo futuras ediciones
        
        Args:
            historial_id: UUID del historial
            usuario: Usuario que cierra el historial
            
        Returns:
            Instancia de ClinicalRecord cerrada
        """
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        historial.cerrar_historial(usuario)
        
        logger.info(f"Historial {historial_id} cerrado por {usuario.username}")
        
        return historial
    
    @staticmethod
    def reabrir_historial(historial_id, usuario):
        """
        Reabre un historial cerrado (acción sensible)
        
        Args:
            historial_id: UUID del historial
            usuario: Usuario que reabre el historial
            
        Returns:
            Instancia de ClinicalRecord reabierta
        """
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        historial.reabrir_historial(usuario)
        
        logger.warning(
            f"Historial {historial_id} reabierto por {usuario.username}"
        )
        
        return historial
    
    @staticmethod
    def eliminar_historial(historial_id):
        """
        Eliminación lógica de un historial
        
        Args:
            historial_id: UUID del historial
            
        Returns:
            Instancia de ClinicalRecord desactivada
        """
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        historial.activo = False
        historial.save()
        
        logger.info(f"Historial {historial_id} eliminado (desactivado)")
        
        return historial
    
    @staticmethod
    def obtener_historial_con_datos_completos(historial_id):
        """
        Obtiene un historial con todas sus relaciones cargadas
        
        Args:
            historial_id: UUID del historial
            
        Returns:
            Instancia de ClinicalRecord con relaciones cargadas
        """
        return ClinicalRecordRepository.obtener_por_id(historial_id)
    
    @staticmethod
    def cargar_datos_iniciales_paciente(paciente_id):
        """
        Carga los datos iniciales de un paciente para crear historial
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            Diccionario con datos pre-cargados
        """
        return RecordLoaderService.cargar_datos_iniciales_paciente(paciente_id)
    
    
    @classmethod
    def agregar_form033_a_historial(
        cls,
        historial_id,
        form033_data,
        usuario,
        observaciones=''
    ):
        """
        Agrega o actualiza el snapshot del Form033 a un historial existente
        
        Args:
            historial_id: UUID del historial
            form033_data: Datos del Form033
            usuario: Usuario que realiza la acción
            observaciones: Observaciones opcionales
        
        Returns:
            Form033Snapshot creado o actualizado
        """
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        
        # Verificar si ya existe un snapshot
        snapshot_existente = Form033StorageService.obtener_snapshot_por_historial(
            historial_id
        )
        
        if snapshot_existente:
            # Actualizar snapshot existente
            snapshot = Form033StorageService.actualizar_snapshot(
                snapshot_id=snapshot_existente.id,
                datos_form033=form033_data,
                observaciones=observaciones
            )
            logger.info(
                f"Snapshot Form033 actualizado para historial {historial_id}"
            )
        else:
            # Crear nuevo snapshot
            snapshot = Form033StorageService.crear_snapshot_desde_datos(
                historial_clinico=historial,
                datos_form033=form033_data,
                usuario=usuario,
                observaciones=observaciones
            )
            logger.info(
                f"Snapshot Form033 creado para historial {historial_id}"
            )
        
        return snapshot
    
    @staticmethod
    def obtener_indicadores_historial(historial_id: str) -> Optional[Dict[str, Any]]:
        try:
            historial = ClinicalRecordRepository.obtener_por_id(historial_id)
            
            indicadores = historial.indicadores_salud_bucal
            
            if not indicadores:
                return None
            
            from ..serializers.oral_health_indicators import OralHealthIndicatorsSerializer
            serializer = OralHealthIndicatorsSerializer(indicadores)
            return serializer.data
        except Exception as e:
            logger.error(f"Error obteniendo indicadores para historial {historial_id}: {str(e)}")
            return None

