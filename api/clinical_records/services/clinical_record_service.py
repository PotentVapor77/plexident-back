"""
Servicio mejorado para lógica de negocio de Historiales Clínicos.
Incluye vinculación automática del Plan de Tratamiento.

CAMBIOS (optimización BD remota lenta):
- crear_historial: se reemplaza ClinicalRecord(**data) + full_clean() + save()
  por ClinicalRecord.objects.create(**data) para ejecutar UN SOLO INSERT
  en lugar de SELECT-validate + INSERT.
- Se elimina la llamada a full_clean() manual antes del save(); Django ya la
  ejecuta internamente al llamar a model.save() cuando el modelo la sobreescribe.
  La única validación explícita necesaria es antes de construir el objeto.
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

from api.clinical_records.services.diagnostico_cie_service import DiagnosticosCIEService
from api.odontogram.services.plan_tratamiento_service import PlanTratamientoService
from api.clinical_records.services.plan_tratamiento_service import PlanTratamientoLinkService


from .number_generator_service import NumberGeneratorService
from .vital_signs_service import VitalSignsService
from .record_loader_service import RecordLoaderService



logger = logging.getLogger(__name__)


class ClinicalRecordService:
    """Servicio para la lógica de negocio de Historiales Clínicos"""
    
    @classmethod
    def crear_historial(cls, data):
        """
        Crea un nuevo historial clínico con datos pre-cargados.
        Vincula automáticamente el plan de tratamiento activo del paciente.

        OPTIMIZACIÓN: se usa objects.create() en lugar de instanciar + full_clean()
        + save() para evitar el SELECT de validación de unicidad que full_clean()
        provoca antes de cada INSERT, lo que en BD remotas genera un round-trip
        extra innecesario (la constraint UNIQUE de la BD ya lo garantiza).
        """
        paciente = data.get('paciente')
        paciente_id = paciente.id
        creado_por = data.get('creado_por')
        
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

                VitalSignsService.limpiar_campos_del_dict(data)
                if motivo_consulta is not None:
                    data['motivo_consulta'] = motivo_consulta
                if enfermedad_actual is not None:
                    data['enfermedad_actual'] = enfermedad_actual
                    
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
            'indices_caries',
        ]
        for seccion in secciones:
            if not data.get(seccion) and ultimos_datos.get(seccion):
                data[seccion] = ultimos_datos[seccion]
        
        # === CARGAR INDICADORES ===
        if not data.get('indicadores_salud_bucal'):
            logger.info(f"Buscando indicadores para paciente {paciente_id}")
            indicadores = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(
                str(paciente_id)
            )
            
            if indicadores:
                data['indicadores_salud_bucal'] = indicadores
                logger.info(f"Indicadores {indicadores.id} encontrados y asociados")
            else:
                logger.info("No hay indicadores previos para este paciente")
        
        # === VINCULAR PLAN DE TRATAMIENTO ACTIVO ===
        if not data.get('plan_tratamiento'):
            logger.info(f"Buscando plan de tratamiento activo para paciente {paciente_id}")
            plan_activo = PlanTratamientoLinkService.obtener_plan_activo_paciente(paciente_id)
            
            if plan_activo:
                data['plan_tratamiento'] = plan_activo
                logger.info(
                    f"Plan de tratamiento {plan_activo.id} vinculado automáticamente "
                    f"al historial para paciente {paciente_id}"
                )
            else:
                logger.warning(
                    f"No se encontró plan de tratamiento activo para paciente {paciente_id}"
                )
        
        # === VINCULAR EXÁMENES COMPLEMENTARIOS ===
        if not data.get('examenes_complementarios'):
            logger.info(f"Buscando exámenes complementarios para paciente {paciente_id}")
            from api.clinical_records.services.examenes_complementarios_service import ExamenesComplementariosLinkService
            ultimo_examen = ExamenesComplementariosLinkService.obtener_ultimo_examen_paciente(paciente_id)
            
            if ultimo_examen:
                data['examenes_complementarios'] = ultimo_examen
                logger.info(
                    f"Exámenes complementarios {ultimo_examen.id} vinculados automáticamente "
                    f"al historial para paciente {paciente_id}"
                )
            else:
                logger.info(
                    f"No se encontraron exámenes complementarios para paciente {paciente_id}"
                )
        
        # === LIMPIEZA DE DATOS ===
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
        
        cls._validar_datos_previo_insert(data, paciente)

        historial = ClinicalRecord.objects.create(**data)
        
        # === GUARDAR DIAGNÓSTICOS CIE SI SE PROPORCIONAN ===
        diagnosticos_data = data.get('diagnosticos_cie', [])
        tipo_carga = data.get('tipo_carga_diagnosticos', 'nuevos')
        
        if diagnosticos_data and creado_por:
            try:
                resultado = DiagnosticosCIEService.cargar_diagnosticos_a_historial(
                    historial_clinico=historial,
                    diagnosticos_data=diagnosticos_data,
                    tipo_carga=tipo_carga,
                    usuario=creado_por
                )
                
                if resultado.get('success'):
                    logger.info(
                        f"Diagnósticos CIE cargados: {resultado.get('total_diagnosticos')} "
                        f"en historial {historial.id}"
                    )
            except Exception as e:
                logger.error(f"Error cargando diagnósticos CIE: {str(e)}")
        
        logger.info(
            f"Historial clínico {historial.id} creado exitosamente para paciente {paciente_id}"
        )
        
        return historial

    @staticmethod
    def _validar_datos_previo_insert(data: dict, paciente) -> None:
        """
        Validaciones de negocio que se ejecutan UNA SOLA VEZ antes del INSERT.
        Reemplaza el full_clean() que el modelo ejecutaba en save() y que
        provocaba queries SELECT adicionales innecesarios.
        """
        # Validar embarazo según sexo
        if data.get('embarazada') == 'SI' and paciente.sexo == 'M':
            raise ValidationError(
                'Un paciente masculino no puede estar embarazado.'
            )
        
        # Validar rol del odontólogo
        odontologo = data.get('odontologo_responsable')
        if odontologo and odontologo.rol != 'Odontologo':
            raise ValidationError('El responsable debe ser un odontólogo.')
    
    @staticmethod
    def _validar_datos_historial(historial):
        """Validaciones de negocio del historial (para uso en update)"""
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
        """Cierra un historial clínico"""
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        historial.cerrar_historial(usuario)
        
        logger.info(f"Historial {historial_id} cerrado por {usuario.username}")
        
        return historial
    
    @staticmethod
    def reabrir_historial(historial_id, usuario):
        """Reabre un historial cerrado"""
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        historial.reabrir_historial(usuario)
        
        logger.warning(
            f"Historial {historial_id} reabierto por {usuario.username}"
        )
        
        return historial
    
    @staticmethod
    def eliminar_historial(historial_id):
        """Eliminación lógica de un historial"""
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        historial.activo = False
        historial.save(update_fields=['activo'])  # Solo actualiza el campo necesario
        
        logger.info(f"Historial {historial_id} eliminado (desactivado)")
        
        return historial
    
    @staticmethod
    def obtener_historial_con_datos_completos(historial_id):
        """Obtiene un historial con todas sus relaciones cargadas"""
        return ClinicalRecordRepository.obtener_por_id(historial_id)
    
    @staticmethod
    def cargar_datos_iniciales_paciente(paciente_id):
        """Carga los datos iniciales de un paciente para crear historial"""
        return RecordLoaderService.cargar_datos_iniciales_paciente(paciente_id)
    
    @classmethod
    def agregar_form033_a_historial(
        cls,
        historial_id,
        form033_data,
        usuario,
        observaciones=''
    ):
        """Agrega o actualiza el snapshot del Form033"""
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        
        snapshot_existente = Form033StorageService.obtener_snapshot_por_historial(
            historial_id
        )
        
        if snapshot_existente:
            snapshot = Form033StorageService.actualizar_snapshot(
                snapshot_id=snapshot_existente.id,
                datos_form033=form033_data,
                observaciones=observaciones
            )
            logger.info(f"Snapshot Form033 actualizado para historial {historial_id}")
        else:
            snapshot = Form033StorageService.crear_snapshot_desde_datos(
                historial_clinico=historial,
                datos_form033=form033_data,
                usuario=usuario,
                observaciones=observaciones
            )
            logger.info(f"Snapshot Form033 creado para historial {historial_id}")
        
        return snapshot
    
    @staticmethod
    def obtener_indicadores_historial(historial_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene indicadores del historial"""
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
    
    @staticmethod
    def cargar_diagnosticos_cie_historial(historial_id, diagnosticos_data, tipo_carga, usuario):
        """Carga diagnósticos CIE-10 al historial"""
        try:
            historial = ClinicalRecord.objects.get(id=historial_id, activo=True)
            
            if historial.estado == 'CERRADO':
                raise ValidationError('No se pueden agregar diagnósticos a un historial cerrado')
            
            resultado = DiagnosticosCIEService.cargar_diagnosticos_a_historial(
                historial_clinico=historial,
                diagnosticos_data=diagnosticos_data,
                tipo_carga=tipo_carga,
                usuario=usuario
            )
            
            return resultado
            
        except ClinicalRecord.DoesNotExist:
            raise ValidationError('Historial clínico no encontrado')