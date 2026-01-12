from typing import Dict, Any, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from api.odontogram.models import (
    PlanTratamiento, SesionTratamiento, Paciente, 
    HistorialOdontograma, DiagnosticoDental, Diente
)
from django.db.models import Prefetch, Q
import uuid

from api.appointment.models import EstadoCita
from api.appointment.services.appointment_service import CitaService
from api.odontogram.services.diagnostico_text_service import construir_texto_procedimiento_desde_diagnosticos

User = get_user_model()


class PlanTratamientoService:
    
    @staticmethod
    def obtener_diagnosticos_ultimo_odontograma(paciente_id: str) -> Dict[str, Any]:
        """
        Obtiene los diagnósticos del último odontograma guardado del paciente.
        Retorna la estructura autocompletada para la sesión.
        """
        try:
            # Obtener el último snapshot completo del odontograma
            ultimo_historial = HistorialOdontograma.objects.filter(
                diente__paciente_id=paciente_id,
                tipo_cambio=HistorialOdontograma.TipoCambio.SNAPSHOT_COMPLETO
            ).order_by('-fecha').first()
            
            if not ultimo_historial:
                # Si no hay snapshot, obtener diagnósticos activos actuales
                return PlanTratamientoService._obtener_diagnosticos_actuales(paciente_id)
            
            # Extraer diagnósticos del snapshot
            odontograma_data = ultimo_historial.datos_nuevos
            diagnosticos = []
            
            for codigo_fdi, superficies in odontograma_data.items():
                for superficie_nombre, diags_list in superficies.items():
                    for diag in diags_list:
                        diagnosticos.append({
                            'id': diag.get('id'),
                            'diente': codigo_fdi,
                            'superficie': superficie_nombre,
                            'diagnostico_key': diag.get('key') or diag.get('procedimientoId'),
                            'diagnostico_nombre': diag.get('nombre'),
                            'siglas': diag.get('siglas'),
                            'color_hex': diag.get('colorHex'),
                            'prioridad': diag.get('prioridad'),
                            'categoria': diag.get('categoria_nombre'),
                            'descripcion': diag.get('descripcion', ''),
                            'estado_tratamiento': diag.get('estadotratamiento', 'diagnosticado'),
                            'atributos_clinicos': diag.get('secondaryOptions', {}),
                        })
            
            return {
                'version_odontograma': str(ultimo_historial.version_id),
                'fecha_odontograma': ultimo_historial.fecha.isoformat(),
                'total_diagnosticos': len(diagnosticos),
                'diagnosticos': diagnosticos
            }
            
        except Exception as e:
            raise ValidationError(f"Error obteniendo diagnósticos: {str(e)}")
    
    @staticmethod
    def _obtener_diagnosticos_actuales(paciente_id: str) -> Dict[str, Any]:
        """Obtiene diagnósticos actuales si no hay snapshot"""
        diagnosticos_activos = DiagnosticoDental.objects.filter(
            superficie__diente__paciente_id=paciente_id,
            activo=True
        ).select_related(
            'diagnostico_catalogo', 
            'diagnostico_catalogo__categoria',
            'superficie__diente'
        ).order_by('superficie__diente__codigo_fdi')
        
        diagnosticos = []
        for diag in diagnosticos_activos:
            diagnosticos.append({
                'id': str(diag.id),
                'diente': diag.superficie.diente.codigo_fdi,
                'superficie': diag.superficie.get_nombre_display(),
                'diagnostico_key': diag.diagnostico_catalogo.key,
                'diagnostico_nombre': diag.diagnostico_catalogo.nombre,
                'siglas': diag.diagnostico_catalogo.siglas,
                'color_hex': diag.diagnostico_catalogo.simbolo_color,
                'prioridad': diag.prioridad_efectiva,
                'categoria': diag.diagnostico_catalogo.categoria.nombre,
                'descripcion': diag.descripcion,
                'estado_tratamiento': diag.estado_tratamiento,
                'atributos_clinicos': diag.atributos_clinicos or {},
            })
        
        return {
            'version_odontograma': None,
            'fecha_odontograma': None,
            'total_diagnosticos': len(diagnosticos),
            'diagnosticos': diagnosticos
        }
    
    @transaction.atomic
    def crear_plan_tratamiento(
        self, 
        paciente_id: str, 
        odontologo_id: int,
        titulo: str = "Plan de Tratamiento",
        notas_generales: str = "",
        usar_ultimo_odontograma: bool = True
    ) -> PlanTratamiento:
        """Crea un nuevo plan de tratamiento"""
        try:
            paciente = Paciente.objects.get(id=paciente_id)
            odontologo = User.objects.get(id=odontologo_id)
        except (Paciente.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Paciente u odontólogo no encontrado")
        
        version_odontograma = None
        if usar_ultimo_odontograma:
            diagnosticos_data = self.obtener_diagnosticos_ultimo_odontograma(paciente_id)
            version_odontograma = diagnosticos_data.get('version_odontograma')
        
        plan = PlanTratamiento.objects.create(
            paciente=paciente,
            titulo=titulo,
            notas_generales=notas_generales,
            creado_por=odontologo,
            version_odontograma=version_odontograma
        )
        
        return plan
    
    @transaction.atomic
    def crear_sesion_tratamiento(
        self,
        plan_tratamiento_id: str,
        odontologo_id: int,
        fecha_programada=None,
        autocompletar_diagnosticos: bool = True,
        procedimientos: List[Dict] | None = None,
        prescripciones: List[Dict] | None = None,
        notas: str = "",
        cita_id: Optional[str] = None,
        diagnosticos_complicaciones: Optional[List[Dict[str, Any]]] = None,
    ) -> SesionTratamiento:
        
        try:
            plan = PlanTratamiento.objects.get(id=plan_tratamiento_id)
            odontologo = User.objects.get(id=odontologo_id)
        except (PlanTratamiento.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Plan de tratamiento u odontólogo no encontrado")

        # Obtener/validar cita si viene
        cita = None
        if cita_id:
            cita = CitaService.obtener_cita_por_id(cita_id)
            if not cita:
                raise ValidationError("Cita no encontrada")
            if not cita.esta_vigente:
                raise ValidationError("La cita no está vigente")
            if cita.paciente_id != plan.paciente_id:
                raise ValidationError("La cita no pertenece al mismo paciente del plan")
            if cita.sesiones.exists():
                raise ValidationError("La cita ya está vinculada a otra sesión")

            if not fecha_programada:
                fecha_programada = cita.fecha
        print(">>> diagnosticos_complicaciones recibido:", diagnosticos_complicaciones)
        # 1) Empezar con lo que viene del front (solo seleccionados)
        diagnosticos_finales: List[Dict[str, Any]] = diagnosticos_complicaciones or []
        print(">>> diagnosticos_finales que se guardan:", diagnosticos_finales)

        # 2) Solo si está activado autocompletar y NO vino nada desde el front
        #if autocompletar_diagnosticos and not diagnosticos_finales:
         #   diagnosticos_data = self.obtener_diagnosticos_ultimo_odontograma(
          #      str(plan.paciente.id)
           # )
            #diagnosticos_finales = diagnosticos_data["diagnosticos"]
        procedimientos = list(procedimientos or [])
        
        if autocompletar_diagnosticos and diagnosticos_finales:
            # Del JSON del front: cada item trae 'diagnostico_key'
            keys_catalogo = [
                item.get("diagnostico_key")
                for item in diagnosticos_finales
                if item.get("diagnostico_key")
            ]

            texto_sugerido = construir_texto_procedimiento_desde_diagnosticos(
                keys_catalogo,
                modo="key",
            )

            if texto_sugerido:
                procedimientos.append(
                    {
                        "descripcion": texto_sugerido,
                        "autogenerado": True,
                    }
                )
        
        
        
        
        # Calcular número de sesión
        ultima_sesion = SesionTratamiento.objects.filter(
            plan_tratamiento=plan
        ).order_by("-numero_sesion").first()
        numero_sesion = (ultima_sesion.numero_sesion + 1) if ultima_sesion else 1

        # Crear sesión con la lista final ya decidida
        sesion = SesionTratamiento.objects.create(
            plan_tratamiento=plan,
            numero_sesion=numero_sesion,
            fecha_programada=fecha_programada,
            diagnosticos_complicaciones=diagnosticos_finales,
            procedimientos=procedimientos,
            prescripciones=prescripciones or [],
            notas=notas,
            odontologo=odontologo,
            cita=cita,
        )

        if cita and cita.estado == EstadoCita.PROGRAMADA:
            CitaService.cambiar_estado_cita(cita.id, EstadoCita.EN_ATENCION)

        return sesion
        
    @transaction.atomic
    def firmar_sesion(
        self,
        sesion_id: str,
        odontologo_id: int,
        firma_digital: str = None
    ) -> SesionTratamiento:
        """Firma una sesión de tratamiento"""
        try:
            sesion = SesionTratamiento.objects.get(id=sesion_id)
            odontologo = User.objects.get(id=odontologo_id)
        except (SesionTratamiento.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Sesión u odontólogo no encontrado")
        
        sesion.firmar_sesion(odontologo, firma_digital)
        return sesion
    
    def obtener_sesiones_pendientes(self, paciente_id: str) -> List[SesionTratamiento]:
        """Obtiene sesiones pendientes de un paciente"""
        return SesionTratamiento.objects.filter(
            plan_tratamiento__paciente_id=paciente_id,
            estado__in=['planificada', 'en_progreso'],
            activo=True
        ).select_related('plan_tratamiento', 'odontologo').order_by('fecha_programada')
        
        
    @staticmethod
    def obtener_diagnosticos_nuevos_version(paciente_id: str, version_id: str) -> Dict[str, Any]:
        """
        Obtiene solo los diagnósticos agregados en una versión específica,
        excluyendo los que ya existían en versiones anteriores.
        """
        try:
            # Obtener el snapshot de la versión actual
            snapshot_actual = HistorialOdontograma.objects.filter(
                diente__paciente_id=paciente_id,
                version_id=version_id,
                tipo_cambio=HistorialOdontograma.TipoCambio.SNAPSHOT_COMPLETO
            ).first()

            if not snapshot_actual:
                return {
                    'version_odontograma': None,
                    'fecha_odontograma': None,
                    'total_diagnosticos': 0,
                    'diagnosticos': []
                }

            # Obtener el snapshot anterior (si existe)
            snapshot_anterior = HistorialOdontograma.objects.filter(
                diente__paciente_id=paciente_id,
                tipo_cambio=HistorialOdontograma.TipoCambio.SNAPSHOT_COMPLETO,
                fecha__lt=snapshot_actual.fecha
            ).order_by('-fecha').first()

            # IDs de diagnósticos anteriores
            diagnosticos_anteriores_ids = set()
            if snapshot_anterior:
                odontograma_anterior = snapshot_anterior.datos_nuevos
                for codigo_fdi, superficies in odontograma_anterior.items():
                    for superficie_nombre, diags_list in superficies.items():
                        for diag in diags_list:
                            diag_id = diag.get('id')
                            if diag_id:
                                diagnosticos_anteriores_ids.add(diag_id)

            # Extraer solo diagnósticos nuevos del snapshot actual
            odontograma_actual = snapshot_actual.datos_nuevos
            diagnosticos_nuevos = []
            
            for codigo_fdi, superficies in odontograma_actual.items():
                for superficie_nombre, diags_list in superficies.items():
                    for diag in diags_list:
                        diag_id = diag.get('id')
                        # Solo agregar si NO estaba en la versión anterior
                        if diag_id and diag_id not in diagnosticos_anteriores_ids:
                            diagnosticos_nuevos.append({
                                'id': diag_id,
                                'diente': codigo_fdi,
                                'superficie': superficie_nombre,
                                'diagnostico_key': diag.get('key') or diag.get('procedimientoId'),
                                'diagnostico_nombre': diag.get('nombre'),
                                'siglas': diag.get('siglas'),
                                'color_hex': diag.get('colorHex'),
                                'prioridad': diag.get('prioridad'),
                                'categoria': diag.get('categoria_nombre'),
                                'descripcion': diag.get('descripcion', ''),
                                'estado_tratamiento': diag.get('estadotratamiento', 'diagnosticado'),
                                'atributos_clinicos': diag.get('secondaryOptions', {}),
                            })

            return {
                'version_odontograma': str(snapshot_actual.version_id),
                'fecha_odontograma': snapshot_actual.fecha.isoformat(),
                'total_diagnosticos': len(diagnosticos_nuevos),
                'diagnosticos': diagnosticos_nuevos
            }

        except Exception as e:
            raise ValidationError(f"Error obteniendo diagnósticos nuevos: {str(e)}")


    # Modificar el método existente para incluir flag de diagnósticos nuevos
    @staticmethod
    def obtener_diagnosticos_ultimo_odontograma(paciente_id: str) -> Dict[str, Any]:
        """
        Obtiene los diagnósticos del último odontograma guardado del paciente.
        Incluye flag 'es_nuevo' para identificar diagnósticos de la última versión.
        """
        try:
            # Obtener el último snapshot completo
            ultimo_historial = HistorialOdontograma.objects.filter(
                diente__paciente_id=paciente_id,
                tipo_cambio=HistorialOdontograma.TipoCambio.SNAPSHOT_COMPLETO
            ).order_by('-fecha').first()

            if not ultimo_historial:
                return PlanTratamientoService._obtener_diagnosticos_actuales(paciente_id)

            # Obtener snapshot anterior para marcar nuevos
            snapshot_anterior = HistorialOdontograma.objects.filter(
                diente__paciente_id=paciente_id,
                tipo_cambio=HistorialOdontograma.TipoCambio.SNAPSHOT_COMPLETO,
                fecha__lt=ultimo_historial.fecha
            ).order_by('-fecha').first()

            diagnosticos_anteriores_ids = set()
            if snapshot_anterior:
                odontograma_anterior = snapshot_anterior.datos_nuevos
                for codigo_fdi, superficies in odontograma_anterior.items():
                    for superficie_nombre, diags_list in superficies.items():
                        for diag in diags_list:
                            diag_id = diag.get('id')
                            if diag_id:
                                diagnosticos_anteriores_ids.add(diag_id)

            # Extraer diagnósticos del snapshot actual con flag de nuevos
            odontograma_data = ultimo_historial.datos_nuevos
            diagnosticos = []
            
            for codigo_fdi, superficies in odontograma_data.items():
                for superficie_nombre, diags_list in superficies.items():
                    for diag in diags_list:
                        diag_id = diag.get('id')
                        es_nuevo = diag_id not in diagnosticos_anteriores_ids if diag_id else True
                        
                        diagnosticos.append({
                            'id': diag_id,
                            'diente': codigo_fdi,
                            'superficie': superficie_nombre,
                            'diagnostico_key': diag.get('key') or diag.get('procedimientoId'),
                            'diagnostico_nombre': diag.get('nombre'),
                            'siglas': diag.get('siglas'),
                            'color_hex': diag.get('colorHex'),
                            'prioridad': diag.get('prioridad'),
                            'categoria': diag.get('categoria_nombre'),
                            'descripcion': diag.get('descripcion', ''),
                            'estado_tratamiento': diag.get('estadotratamiento', 'diagnosticado'),
                            'atributos_clinicos': diag.get('secondaryOptions', {}),
                            'es_nuevo': es_nuevo  # ← NUEVO FLAG
                        })

            return {
                'version_odontograma': str(ultimo_historial.version_id),
                'fecha_odontograma': ultimo_historial.fecha.isoformat(),
                'total_diagnosticos': len(diagnosticos),
                'diagnosticos': diagnosticos
            }

        except Exception as e:
            raise ValidationError(f"Error obteniendo diagnósticos: {str(e)}")
