# odontogram/services/odontogram_services.py
"""
Servicios para la nueva estructura de Odontograma
Maneja: Paciente -> Diente -> Superficie -> DiagnosticoDental
"""

from typing import List, Dict, Any, Optional
import uuid
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from api.odontogram.models import (
    Paciente,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma,
    Diagnostico,
)
from django.db.models import Prefetch
User = get_user_model()


def _es_uuid_valido(valor: str) -> bool:
    """
    Devuelve True solo si valor es un UUID válido.
    Sirve para ignorar IDs temporales del frontend (Date.now()-random).
    """
    try:
        uuid.UUID(str(valor))
        return True
    except (ValueError, TypeError):
        return False


class OdontogramaService:
    """
    Servicio para gestionar odontogramas de pacientes.
    Conecta el frontend con la nueva estructura de BD.
    """

    @transaction.atomic
    def guardar_odontograma_completo(
        self,
        paciente_id: str,
        odontologo_id: int,
        odontograma_data: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ) -> Dict[str, Any]:
        """
        Guarda el odontograma completo de un paciente.

        Reglas:
        - Si viene un ID que es UUID válido -> intenta editar por ID.
        - Si no hay ID o el ID no es UUID válido -> usa equivalencia por attrs.
        - Si no existe ni por ID ni por attrs -> crea diagnóstico nuevo.
        """
        
        try:
            paciente = Paciente.objects.get(id=paciente_id)
            odontologo = User.objects.get(id=odontologo_id)
        except (Paciente.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Paciente u odontólogo no encontrado")

        resultado = {
            "paciente_id": str(paciente.id),
            "dientes_procesados": [],
            "diagnosticos_guardados": 0,
            "diagnosticos_modificados": 0, 
            "errores": [],
        }
        
        version_id = uuid.uuid4()
        now = timezone.now()
        
        # Procesar cada diente
        for codigo_fdi, superficies_dict in odontograma_data.items():
            try:
                diente, created = Diente.objects.get_or_create(
                    paciente=paciente,
                    codigo_fdi=codigo_fdi,
                )
                resultado["dientes_procesados"].append(codigo_fdi)

                # Procesar cada superficie
                for nombre_superficie, diagnosticos_list in superficies_dict.items():
                    try:
                        superficie, _ = SuperficieDental.objects.get_or_create(
                            diente=diente,
                            nombre=nombre_superficie,
                        )

                        print("DEBUG diagnosticos_list:", diagnosticos_list)

                        # Procesar cada diagnóstico
                        for diag_data in diagnosticos_list:
                            try:
                                diagnostico_cat = Diagnostico.objects.get(
                                    key=diag_data["procedimientoId"],
                                    activo=True,
                                )

                                attrs = diag_data.get("secondaryOptions", {}) or {}
                                descripcion = diag_data.get("descripcion", "") or ""
                                diag_id = diag_data.get("id")

                                # 1) Si viene ID y es UUID válido, intentar EDITAR por ID
                                if diag_id and _es_uuid_valido(diag_id):
                                    try:
                                        diag_dental = DiagnosticoDental.objects.get(
                                            id=diag_id,
                                            superficie=superficie,
                                            diagnostico_catalogo=diagnostico_cat,
                                            activo=True,
                                        )
                                    except DiagnosticoDental.DoesNotExist:
                                        diag_dental = None
                                    
                                    if diag_dental:
                                        datos_anteriores = {
                                            "descripcion": diag_dental.descripcion,
                                            "atributos_clinicos": diag_dental.atributos_clinicos,
                                        }
                                        
                                        datos_nuevos = {
                                            "descripcion": descripcion,
                                            "atributos_clinicos": attrs,
                                        }
                                        
                                        ha_cambios = (
                                            datos_anteriores["descripcion"] != datos_nuevos["descripcion"] or
                                            datos_anteriores["atributos_clinicos"] != datos_nuevos["atributos_clinicos"]
                                        )
                                        
                                        if ha_cambios:
                                            diag_dental.descripcion = descripcion
                                            diag_dental.atributos_clinicos = attrs
                                            diag_dental.save()
                                            
                                            HistorialOdontograma.objects.create(
                                                diente=superficie.diente,
                                                tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO,
                                                descripcion=(
                                                    f"Diagnóstico {diagnostico_cat.nombre} "
                                                    f"modificado en {superficie.get_nombre_display()}"
                                                ),
                                                odontologo=odontologo,
                                                datos_anteriores=datos_anteriores,
                                                datos_nuevos=datos_nuevos,
                                                fecha=now,
                                                version_id=version_id,
                                            )
                                            resultado["diagnosticos_modificados"] += 1  
                                            print(f"[DEBUG] Modificado con cambios: {diag_id}")
                                        else:
                                            print(f"[DEBUG] Sin cambios, no se registra: {diag_id}")
                                        
                                        continue
                                
                                # 2) Editar por equivalencia
                                existente = DiagnosticoDental.objects.filter(
                                    superficie=superficie,
                                    diagnostico_catalogo=diagnostico_cat,
                                    atributos_clinicos=attrs,
                                    activo=True,
                                ).first()
                                
                                if existente:
                                    datos_anteriores = {
                                        "descripcion": existente.descripcion,
                                        "atributos_clinicos": existente.atributos_clinicos,
                                    }
                                    
                                    datos_nuevos = {
                                        "descripcion": descripcion,
                                        "atributos_clinicos": attrs,
                                    }
                                    
                                    ha_cambios = (
                                        datos_anteriores["descripcion"] != datos_nuevos["descripcion"] or
                                        datos_anteriores["atributos_clinicos"] != datos_nuevos["atributos_clinicos"]
                                    )
                                    
                                    if ha_cambios:
                                        existente.descripcion = descripcion
                                        existente.atributos_clinicos = attrs
                                        existente.save()
                                        
                                        HistorialOdontograma.objects.create(
                                            diente=superficie.diente,
                                            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO,
                                            descripcion=(
                                                f"Diagnóstico {diagnostico_cat.nombre} "
                                                f"modificado en {superficie.get_nombre_display()}"
                                            ),
                                            odontologo=odontologo,
                                            datos_anteriores=datos_anteriores,
                                            datos_nuevos=datos_nuevos,
                                            fecha=now,
                                            version_id=version_id,
                                        )
                                        resultado["diagnosticos_modificados"] += 1 
                                        print(f"[DEBUG] Modificado por attrs: {existente.id}")
                                    else:
                                        print(f"[DEBUG] Sin cambios por attrs: {existente.id}")
                                    
                                    continue

                                # 3) Alta nueva real
                                print(
                                    "DEBUG: creando nuevo diagnostico",
                                    diagnostico_cat.key,
                                    attrs,
                                )
                                diag_dental = DiagnosticoDental.objects.create(
                                    superficie=superficie,
                                    diagnostico_catalogo=diagnostico_cat,
                                    odontologo=odontologo,
                                    descripcion=descripcion,
                                    atributos_clinicos=attrs,
                                    estado_tratamiento=DiagnosticoDental.EstadoTratamiento.DIAGNOSTICADO,
                                )

                                HistorialOdontograma.objects.create(
                                    diente=diente,
                                    tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_AGREGADO,
                                    descripcion=(
                                        f"Diagnóstico {diagnostico_cat.nombre} agregado en "
                                        f"{superficie.get_nombre_display()}"
                                    ),
                                    odontologo=odontologo,
                                    datos_nuevos={
                                        "diagnostico": diagnostico_cat.key,
                                        "superficie": nombre_superficie,
                                        "atributos": attrs,
                                    },
                                    fecha=now,
                                    version_id=version_id, 
                                )

                                resultado["diagnosticos_guardados"] += 1

                            except Diagnostico.DoesNotExist:
                                resultado["errores"].append(
                                    f"Diagnóstico {diag_data.get('procedimientoId')} no encontrado"
                                )
                            except Exception as e:
                                resultado["errores"].append(
                                    f"Error guardando diagnóstico en {codigo_fdi}/{nombre_superficie}: {str(e)}"
                                )

                    except Exception as e:
                        resultado["errores"].append(
                            f"Error procesando superficie {nombre_superficie}: {str(e)}"
                        )

            except Exception as e:
                resultado["errores"].append(
                    f"Error procesando diente {codigo_fdi}: {str(e)}"
                )

        total_cambios = resultado["diagnosticos_guardados"] + resultado["diagnosticos_modificados"]
        
        if total_cambios > 0 and resultado["dientes_procesados"]:
            primer_diente = Diente.objects.filter(
                paciente=paciente,
                codigo_fdi=resultado["dientes_procesados"][0]
            ).first()
            
            if primer_diente:
                odontograma_snapshot = {}
                
                for codigo_fdi, superficies_dict in odontograma_data.items():
                    odontograma_snapshot[codigo_fdi] = {}
                    
                    for nombre_superficie, diagnosticos_list in superficies_dict.items():
                        odontograma_snapshot[codigo_fdi][nombre_superficie] = []
                        
                        for diag_data in diagnosticos_list:
                            try:
                                diagnostico_cat = Diagnostico.objects.select_related(
                                    'categoria'
                                ).prefetch_related(
                                    'areas_relacionadas__area'
                                ).get(
                                    key=diag_data["procedimientoId"],
                                    activo=True,
                                )
                                
                                diag_enriquecido = {
                                    "id": diag_data.get("id"),
                                    "procedimientoId": diagnostico_cat.key,
                                    "key": diagnostico_cat.key,
                                    "nombre": diagnostico_cat.nombre,
                                    "siglas": diagnostico_cat.siglas,
                                    "colorHex": diagnostico_cat.simbolo_color,  
                                    "prioridad": diagnostico_cat.prioridad,
                                    "afectaArea": list(
                                        diagnostico_cat.areas_relacionadas.values_list(
                                            'area__key', flat=True
                                        )
                                    ),
                                    "secondaryOptions": diag_data.get("secondaryOptions", {}),
                                    "descripcion": diag_data.get("descripcion", ""),
                                }
                                
                                odontograma_snapshot[codigo_fdi][nombre_superficie].append(
                                    diag_enriquecido
                                )
                            except Diagnostico.DoesNotExist:
                                # Si el diagnóstico no existe, mantener datos originales
                                odontograma_snapshot[codigo_fdi][nombre_superficie].append(diag_data)
                
                # Crear registro maestro del snapshot
                HistorialOdontograma.objects.create(
                    diente=primer_diente,
                    tipo_cambio=HistorialOdontograma.TipoCambio.SNAPSHOT_COMPLETO,
                    descripcion=(
                        f"Odontograma guardado: {resultado['diagnosticos_guardados']} diagnósticos nuevos, "
                        f"{resultado['diagnosticos_modificados']} modificados en "
                        f"{len(resultado['dientes_procesados'])} dientes"
                    ),
                    odontologo=odontologo,
                    datos_nuevos=odontograma_snapshot,  
                    fecha=now,
                    version_id=version_id,
                )
                print(f"[DEBUG] Snapshot completo enriquecido creado: version_id={version_id}")

        resultado["version_id"] = str(version_id)
        resultado["tiene_cambios"] = total_cambios > 0
        
        # Invalidar caché
        cache_key = f'odontograma:completo:{paciente_id}'
        cache.delete(cache_key)

        return resultado

    def obtener_odontograma_completo(self, paciente_id: str) -> Dict[str, Any]:
        """
        Obtiene el odontograma completo de un paciente
        OPTIMIZADO con prefetch_related anidado y caché
        """
        # 1. Intentar obtener del caché primero
        cache_key = f'odontograma:completo:{paciente_id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # 2. Si no hay caché, consultar BD
        try:
            paciente = Paciente.objects.get(id=paciente_id)
        except Paciente.DoesNotExist:
            raise ValidationError("Paciente no encontrado")
        
        odontograma_data = {}
        
        # 3. Prefetch anidado profundo
        dientes = Diente.objects.filter(
            paciente=paciente
        ).prefetch_related(
            Prefetch(
                'superficies',
                queryset=SuperficieDental.objects.prefetch_related(
                    Prefetch(
                        'diagnosticos',
                        queryset=DiagnosticoDental.objects.filter(
                            activo=True
                        ).select_related(
                            'diagnostico_catalogo',
                            'diagnostico_catalogo__categoria',
                            'odontologo'
                        ).prefetch_related(
                            'diagnostico_catalogo__areas_relacionadas__area'
                        )
                    )
                )
            )
        ).order_by('codigo_fdi')
        
        # 4. Construir estructura de datos
        for diente in dientes:
            codigo_fdi = diente.codigo_fdi
            odontograma_data[codigo_fdi] = {}
            
            for superficie in diente.superficies.all():
                odontograma_data[codigo_fdi][superficie.nombre] = []
                
                for diag_dental in superficie.diagnosticos.all():
                    odontograma_data[codigo_fdi][superficie.nombre].append({
                        'id': str(diag_dental.id),
                        'procedimientoId': diag_dental.diagnostico_catalogo.key,
                        'nombre': diag_dental.diagnostico_catalogo.nombre,
                        'siglas': diag_dental.diagnostico_catalogo.siglas,
                        'colorHex': diag_dental.diagnostico_catalogo.simbolo_color,  
                        'secondaryOptions': diag_dental.atributos_clinicos,
                        'descripcion': diag_dental.descripcion,
                        'afectaArea': list(
                            diag_dental.diagnostico_catalogo.areas_relacionadas.values_list(
                                'area__key', flat=True
                            )
                        ),
                        'estado_tratamiento': diag_dental.estado_tratamiento,
                        'prioridad': diag_dental.prioridad_efectiva,
                        'fecha': diag_dental.fecha.isoformat(),
                        'odontologo': diag_dental.odontologo.get_full_name(),
                    })
        
        # 5. Construir respuesta
        result = {
            'paciente_id': str(paciente.id),
            'paciente_nombre': f"{paciente.nombres} {paciente.apellidos}",
            'odontograma_data': odontograma_data,
            'fecha_obtension': timezone.now().isoformat(),
        }
        
        # 6. Guardar en caché por 5 minutos
        cache.set(cache_key, result, timeout=300)
        
        return result


    @transaction.atomic
    def marcar_diente_ausente(
        self,
        paciente_id: str,
        codigo_fdi: str,
        odontologo_id: int
    ) -> Diente:
        """
        Marca un diente como ausente y registra en historial
        """
        try:
            paciente = Paciente.objects.get(id=paciente_id)
            odontologo = User.objects.get(id=odontologo_id)
        except (Paciente.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Paciente u odontólogo no encontrado")

        diente, _ = Diente.objects.get_or_create(
            paciente=paciente,
            codigo_fdi=codigo_fdi
        )

        # Cambiar estado
        era_ausente = diente.ausente
        diente.ausente = True
        diente.save()

        # Crear historial
        if not era_ausente:
            HistorialOdontograma.objects.create(
                diente=diente,
                tipo_cambio=HistorialOdontograma.TipoCambio.DIENTE_MARCADO_AUSENTE,
                descripcion=f"Diente {codigo_fdi} marcado como ausente",
                odontologo=odontologo,
                datos_nuevos={'ausente': True}
            )

        return diente

    @transaction.atomic
    def marcar_diagnostico_tratado(
        self,
        diagnostico_id: str,
        odontologo_id: int
    ) -> DiagnosticoDental:
        """
        Marca un diagnóstico como 'Tratado' y registra el cambio en el historial.
        """
        try:
            diagnostico = DiagnosticoDental.objects.select_for_update().get(id=diagnostico_id, activo=True)
            odontologo = User.objects.get(id=odontologo_id)
        except (DiagnosticoDental.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Diagnóstico u odontólogo no encontrado")

        datos_anteriores = {
            'estado_tratamiento': diagnostico.estado_tratamiento,
            'fecha_tratamiento': diagnostico.fecha_tratamiento.isoformat() if diagnostico.fecha_tratamiento else None
        }

        # Actualizar estado y fecha
        diagnostico.estado_tratamiento = DiagnosticoDental.EstadoTratamiento.TRATADO
        diagnostico.fecha_tratamiento = timezone.now()
        diagnostico.save()

        datos_nuevos = {
            'estado_tratamiento': diagnostico.estado_tratamiento,
            'fecha_tratamiento': diagnostico.fecha_tratamiento.isoformat()
        }

        # Crear registro en el historial
        HistorialOdontograma.objects.create(
            diente=diagnostico.diente,
            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_TRATADO,
            descripcion=f"Diagnóstico '{diagnostico.diagnostico_catalogo.nombre}' marcado como Tratado en la superficie {diagnostico.superficie.get_nombre_display()}",
            odontologo=odontologo,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        return diagnostico

    @transaction.atomic
    def eliminar_diagnostico(
        self,
        diagnostico_id: str,
        odontologo_id: int
    ) -> bool:
        """
        Elimina un diagnóstico (soft delete) y registra en historial
        """
        try:
            diagnostico = DiagnosticoDental.objects.get(id=diagnostico_id)
            odontologo = User.objects.get(id=odontologo_id)
        except (DiagnosticoDental.DoesNotExist, User.DoesNotExist):
            return False

        # Soft delete
        diagnostico.activo = False
        diagnostico.save()

        # Crear historial
        HistorialOdontograma.objects.create(
            diente=diagnostico.diente,
            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_ELIMINADO,
            descripcion=f"Diagnóstico {diagnostico.diagnostico_catalogo.nombre} eliminado de {diagnostico.superficie.get_nombre_display()}",
            odontologo=odontologo,
            datos_anteriores={
                'diagnostico': diagnostico.diagnostico_catalogo.key,
                'superficie': diagnostico.superficie.nombre,
            }
            
        )

        return True

    @transaction.atomic
    def actualizar_diagnostico(
        self,
        diagnostico_id: str,
        descripcion: Optional[str] = None,
        atributos_clinicos: Optional[Dict] = None,
        estado_tratamiento: Optional[str] = None,
        prioridad_asignada: Optional[int] = None,
        fecha_tratamiento: Optional[str] = None,
        diagnostico_catalogo_id: Optional[int] = None,
        odontologo_id: Optional[int] = None
    ) -> Optional[DiagnosticoDental]:
        """
        Actualiza un diagnóstico y registra cambios en historial
        """
        try:
            diagnostico = DiagnosticoDental.objects.select_for_update().get(id=diagnostico_id, activo=True)
            if odontologo_id:
                odontologo = User.objects.get(id=odontologo_id)
            else:
                odontologo = diagnostico.odontologo
        except (DiagnosticoDental.DoesNotExist, User.DoesNotExist):
            return None

        # Guardar datos anteriores para historial
        datos_anteriores = {
            'descripcion': diagnostico.descripcion,
            'atributos_clinicos': diagnostico.atributos_clinicos,
            'estado_tratamiento': diagnostico.estado_tratamiento,
            'prioridad_asignada': diagnostico.prioridad_asignada,
            'fecha_tratamiento': diagnostico.fecha_tratamiento,
            'diagnostico_catalogo_id': diagnostico.diagnostico_catalogo_id,
        }

        # Actualizar campos
        if descripcion is not None:
            diagnostico.descripcion = descripcion
        if atributos_clinicos is not None:
            # Merge con atributos existentes
            current_attrs = diagnostico.atributos_clinicos or {}
            current_attrs.update(atributos_clinicos)
            diagnostico.atributos_clinicos = current_attrs
        if estado_tratamiento is not None:
            diagnostico.estado_tratamiento = estado_tratamiento
        if prioridad_asignada is not None:
            if not 1 <= prioridad_asignada <= 5:
                raise ValidationError("Prioridad debe estar entre 1 y 5")
            diagnostico.prioridad_asignada = prioridad_asignada
        if fecha_tratamiento is not None:
            diagnostico.fecha_tratamiento = fecha_tratamiento
        if diagnostico_catalogo_id is not None:
            diagnostico.diagnostico_catalogo_id = diagnostico_catalogo_id
        if odontologo_id is not None:
            diagnostico.odontologo_id = odontologo_id

        diagnostico.save()

        # Crear historial de cambios
        datos_nuevos = {
            'descripcion': diagnostico.descripcion,
            'atributos_clinicos': diagnostico.atributos_clinicos,
            'estado_tratamiento': diagnostico.estado_tratamiento,
            'prioridad_asignada': diagnostico.prioridad_asignada,
            'fecha_tratamiento': diagnostico.fecha_tratamiento,
            'diagnostico_catalogo_id': diagnostico.diagnostico_catalogo_id,
        }

        HistorialOdontograma.objects.create(
            diente=diagnostico.diente,
            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO,
            descripcion=f"Diagnóstico {diagnostico.diagnostico_catalogo.nombre} modificado",
            odontologo=odontologo,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        return diagnostico

    

    def obtener_diagnosticos_paciente(
        self,
        paciente_id: str,
        estado_tratamiento: Optional[str] = None
    ) -> List[DiagnosticoDental]:
        """
        Obtiene todos los diagnósticos de un paciente
        opcionalmente filtrados por estado
        """
        try:
            paciente = Paciente.objects.get(id=paciente_id)
        except Paciente.DoesNotExist:
            return []

        # Obtener todos los diagnósticos del paciente
        diagnosticos = DiagnosticoDental.objects.filter(
            superficie__diente__paciente=paciente,
            activo=True
        ).select_related(
            'diagnostico_catalogo',
            'superficie__diente',
            'odontologo'
        )

        if estado_tratamiento:
            diagnosticos = diagnosticos.filter(estado_tratamiento=estado_tratamiento)

        return list(diagnosticos)
    
    def aplicar_diagnostico_desde_frontend(diente, superficie_id_frontend, diagnostico_key, **kwargs):

        # 1. Normalizar superficie
        nombre_superficie = SuperficieDental.normalizar_superficie_frontend(
            superficie_id_frontend
        )
        
        # 2. Crear o obtener SuperficieDental
        superficie, created = SuperficieDental.objects.get_or_create(
            diente=diente,
            nombre=nombre_superficie
        )
        
        # 3. Obtener diagnóstico del catálogo
        diagnostico = Diagnostico.objects.get(key=diagnostico_key, activo=True)
        
        # 4. Validar que el diagnóstico sea aplicable a esa área
        area_superficie = superficie.area_anatomica
        if not diagnostico.areas_relacionadas.filter(area__key=area_superficie).exists():
            raise ValidationError(
                f"El diagnóstico '{diagnostico.nombre}' no es aplicable a {area_superficie}"
            )
        
        # 5. Crear DiagnosticoDental
        diagnostico_dental = DiagnosticoDental.objects.create(
            superficie=superficie,
            diagnostico_catalogo=diagnostico,
            **kwargs
        )
    
        return diagnostico_dental


