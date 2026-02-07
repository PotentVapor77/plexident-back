# src/api/odontogram/views/diagnostico_cie_views.py

import logging
from datetime import datetime, timedelta
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from api.odontogram.models import DiagnosticoDental, Paciente, HistorialOdontograma
from api.odontogram.serializers.diagnostico_cie_serializer import DiagnosticoCIESerializer

logger = logging.getLogger(__name__)


class DiagnosticoCIEPagination(PageNumberPagination):
    """Paginación para lista de diagnósticos con CIE-10"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class DiagnosticoCIEViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para listar diagnósticos con información CIE-10
    Permite filtrar por paciente, fecha y tipo de diagnóstico
    """
    serializer_class = DiagnosticoCIESerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DiagnosticoCIEPagination
    
    def get_queryset(self):
        """
        Retorna diagnósticos activos con prefetch de relaciones
        """
        queryset = DiagnosticoDental.objects.filter(
            activo=True
        ).select_related(
            'diagnostico_catalogo',
            'superficie',
            'superficie__diente',
            'superficie__diente__paciente',
            'odontologo'
        ).order_by('-fecha')
        
        # Filtros opcionales
        paciente_id = self.request.query_params.get('paciente_id')
        fecha_desde = self.request.query_params.get('fecha_desde')
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        tipo_diagnostico = self.request.query_params.get('tipo_diagnostico')
        estado_tratamiento = self.request.query_params.get('estado_tratamiento')
        codigo_icd10 = self.request.query_params.get('codigo_icd10')
        
        if paciente_id:
            queryset = queryset.filter(superficie__diente__paciente_id=paciente_id)
        
        if fecha_desde:
            try:
                fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d')
                queryset = queryset.filter(fecha__date__gte=fecha_desde_obj)
            except ValueError:
                logger.warning(f"Formato de fecha_desde inválido: {fecha_desde}")
        
        if fecha_hasta:
            try:
                fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d')
                # Añadir un día para incluir la fecha completa
                fecha_hasta_obj = fecha_hasta_obj + timedelta(days=1)
                queryset = queryset.filter(fecha__date__lt=fecha_hasta_obj)
            except ValueError:
                logger.warning(f"Formato de fecha_hasta inválido: {fecha_hasta}")
        
        if tipo_diagnostico:
            queryset = queryset.filter(tipo_diagnostico=tipo_diagnostico)
        
        if estado_tratamiento:
            queryset = queryset.filter(estado_tratamiento=estado_tratamiento)
        
        if codigo_icd10:
            queryset = queryset.filter(diagnostico_catalogo__codigo_icd10=codigo_icd10)
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='ultimo-snapshot/(?P<paciente_id>[^/.]+)')
    def ultimo_snapshot_diagnosticos(self, request, paciente_id=None):
        """
        GET /api/diagnosticos-cie/ultimo-snapshot/{paciente_id}/
        
        Versión mejorada: Busca diagnósticos con mismo version_id o por fecha cercana
        """
        try:
            # 1. Obtener el último snapshot
            from api.odontogram.models import HistorialOdontograma
            
            ultimo_snapshot = HistorialOdontograma.objects.filter(
                diente__paciente_id=paciente_id,
                tipo_cambio=HistorialOdontograma.TipoCambio.SNAPSHOT_COMPLETO
            ).order_by('-fecha').first()
            
            if not ultimo_snapshot:
                return Response({
                    'error': 'No se encontró ningún snapshot para este paciente',
                    'paciente_id': paciente_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            version_id = ultimo_snapshot.version_id
            fecha_snapshot = ultimo_snapshot.fecha
            odontologo_snapshot = ultimo_snapshot.odontologo
            
            # 2. INTENTAR: Buscar diagnósticos por version_id en datos_nuevos
            # Primero, buscar en el historial cambios de esta versión
            cambios = HistorialOdontograma.objects.filter(
                version_id=version_id,
                diente__paciente_id=paciente_id,
                tipo_cambio__in=[
                    HistorialOdontograma.TipoCambio.DIAGNOSTICO_AGREGADO,
                    HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO
                ]
            )
            
            # Extraer IDs de diagnósticos del campo datos_nuevos
            diagnostico_ids = []
            for cambio in cambios:
                datos_nuevos = cambio.datos_nuevos
                # El ID podría estar en diferentes campos
                if isinstance(datos_nuevos, dict):
                    # Buscar en diferentes posibles nombres de campo
                    for key in ['id', 'diagnostico_id', 'diagnostico_dental_id', 'uuid']:
                        if key in datos_nuevos:
                            diagnostico_ids.append(datos_nuevos[key])
                            break
            
            # 3. Si encontramos IDs, buscar esos diagnósticos
            if diagnostico_ids:
                diagnosticos = DiagnosticoDental.objects.filter(
                    id__in=diagnostico_ids,
                    activo=True
                ).select_related(
                    'diagnostico_catalogo',
                    'superficie',
                    'superficie__diente',
                    'superficie__diente__paciente',
                    'odontologo'
                )
                metodo = 'por_ids_del_historial'
            
            else:
                # 4. FALLBACK: Buscar por fecha cercana y mismo odontólogo
                import datetime
                tiempo_ventana = datetime.timedelta(minutes=60)
                fecha_inicio = fecha_snapshot - tiempo_ventana
                fecha_fin = fecha_snapshot + tiempo_ventana
                
                diagnosticos = DiagnosticoDental.objects.filter(
                    superficie__diente__paciente_id=paciente_id,
                    fecha__range=(fecha_inicio, fecha_fin),
                    activo=True
                )
                
                # Filtrar por mismo odontólogo si está disponible
                if odontologo_snapshot:
                    diagnosticos = diagnosticos.filter(odontologo=odontologo_snapshot)
                
                diagnosticos = diagnosticos.select_related(
                    'diagnostico_catalogo',
                    'superficie',
                    'superficie__diente',
                    'superficie__diente__paciente',
                    'odontologo'
                ).order_by('-fecha')
                metodo = 'por_fecha_y_odontologo'
            
            # 5. Serializar
            serializer = self.get_serializer(diagnosticos, many=True)
            
            # 6. Estadísticas
            total_cambios = cambios.count()
            creados = cambios.filter(
                tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_AGREGADO
            ).count()
            modificados = cambios.filter(
                tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO
            ).count()
            
            eliminados = HistorialOdontograma.objects.filter(
                version_id=version_id,
                diente__paciente_id=paciente_id,
                tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_ELIMINADO
            ).count()
            
            return Response({
                'paciente_id': paciente_id,
                'version_id': str(version_id),
                'fecha_snapshot': fecha_snapshot,
                'snapshot_info': {
                    'id': ultimo_snapshot.id,
                    'descripcion': ultimo_snapshot.descripcion,
                    'odontologo': ultimo_snapshot.odontologo.get_full_name() if ultimo_snapshot.odontologo else None
                },
                'metodo_busqueda': metodo,
                'estadisticas': {
                    'total_diagnosticos_encontrados': diagnosticos.count(),
                    'ids_encontrados_en_historial': len(diagnostico_ids),
                    'cambios_en_historial': total_cambios,
                    'creados_en_snapshot': creados,
                    'modificados_en_snapshot': modificados,
                    'eliminados_en_snapshot': eliminados
                },
                'diagnosticos': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'Error interno: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='por-version/(?P<version_id>[^/.]+)')
    def diagnosticos_por_version(self, request, version_id=None):
        """
        GET /api/diagnosticos-cie/por-version/{version_id}/
        
        Retorna todos los diagnósticos activos de una versión específica
        """
        # 1. Obtener todos los cambios de diagnóstico de esta versión
        cambios = HistorialOdontograma.objects.filter(
            version_id=version_id
        ).filter(
            Q(tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_AGREGADO) |
            Q(tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO)
        )
        
        # 2. Extraer IDs de diagnósticos de esta versión
        diagnostico_ids = set()
        for cambio in cambios:
            if 'diagnostico_id' in cambio.datos_nuevos:
                diagnostico_ids.add(cambio.datos_nuevos['diagnostico_id'])
        
        # 3. Obtener diagnósticos actuales (activos)
        diagnosticos = DiagnosticoDental.objects.filter(
            id__in=list(diagnostico_ids),
            activo=True
        ).select_related(
            'diagnostico_catalogo',
            'superficie',
            'superficie__diente',
            'superficie__diente__paciente',
            'odontologo'
        )
        
        # 4. Serializar
        serializer = self.get_serializer(diagnosticos, many=True)
        
        # 5. Obtener info del snapshot
        snapshot = HistorialOdontograma.objects.filter(
            version_id=version_id,
            tipo_cambio=HistorialOdontograma.TipoCambio.SNAPSHOT_COMPLETO
        ).first()
        
        snapshot_info = None
        if snapshot:
            snapshot_info = {
                'id': snapshot.id,
                'fecha': snapshot.fecha,
                'odontologo': snapshot.odontologo.get_full_name() if snapshot.odontologo else None,
                'paciente_id': snapshot.diente.paciente_id if snapshot.diente else None,
                'paciente_nombre': f"{snapshot.diente.paciente.nombres} {snapshot.diente.paciente.apellidos}" if snapshot.diente and snapshot.diente.paciente else None
            }
        
        return Response({
            'version_id': version_id,
            'snapshot_info': snapshot_info,
            'total_diagnosticos': diagnosticos.count(),
            'diagnosticos': serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='cambios-version/(?P<version_id>[^/.]+)')
    def cambios_por_version(self, request, version_id=None):
        """
        GET /api/diagnosticos-cie/cambios-version/{version_id}/
        
        Retorna los cambios de diagnóstico de una versión específica
        (No los diagnósticos actuales, sino los cambios registrados)
        """
        from api.odontogram.serializers import HistorialOdontogramaSerializer
        
        cambios = HistorialOdontograma.objects.filter(
            version_id=version_id
        ).filter(
            Q(tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_AGREGADO) |
            Q(tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO) |
            Q(tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_ELIMINADO)
        ).select_related(
            'odontologo',
            'diente',
            'diente__paciente'
        ).order_by('fecha')
        
        serializer = HistorialOdontogramaSerializer(cambios, many=True)
        
        # Resumen de cambios
        resumen = {
            'agregados': cambios.filter(tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_AGREGADO).count(),
            'modificados': cambios.filter(tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO).count(),
            'eliminados': cambios.filter(tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_ELIMINADO).count(),
            'total': cambios.count()
        }
        
        return Response({
            'version_id': version_id,
            'resumen_cambios': resumen,
            'cambios': serializer.data
        })
        
    @action(detail=False, methods=['get'], url_path='nuevos-ultimo-snapshot/(?P<paciente_id>[^/.]+)')
    def nuevos_ultimo_snapshot(self, request, paciente_id=None):
        """
        GET /api/diagnosticos-cie/nuevos-ultimo-snapshot/{paciente_id}/
        
        Retorna SOLO los diagnósticos NUEVOS creados en el último snapshot
        """
        try:
            # 1. Obtener el último snapshot
            from api.odontogram.models import HistorialOdontograma
            
            ultimo_snapshot = HistorialOdontograma.objects.filter(
                diente__paciente_id=paciente_id,
                tipo_cambio=HistorialOdontograma.TipoCambio.SNAPSHOT_COMPLETO
            ).order_by('-fecha').first()
            
            if not ultimo_snapshot:
                return Response({
                    'error': 'No se encontró snapshot',
                    'paciente_id': paciente_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            version_id = ultimo_snapshot.version_id
            
            # 2. Obtener SOLO diagnósticos NUEVOS de esa versión
            cambios_nuevos = HistorialOdontograma.objects.filter(
                version_id=version_id,
                diente__paciente_id=paciente_id,
                tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_AGREGADO
            )
            
            # 3. Extraer IDs de diagnósticos nuevos
            diagnostico_ids = []
            for cambio in cambios_nuevos:
                if 'diagnostico_id' in cambio.datos_nuevos:
                    diagnostico_ids.append(cambio.datos_nuevos['diagnostico_id'])
            
            # 4. Obtener diagnósticos actuales
            diagnosticos = DiagnosticoDental.objects.filter(
                id__in=diagnostico_ids,
                activo=True
            ).select_related(
                'diagnostico_catalogo',
                'superficie',
                'superficie__diente',
                'superficie__diente__paciente',
                'odontologo'
            )
            
            # 5. Serializar
            serializer = self.get_serializer(diagnosticos, many=True)
            
            return Response({
                'paciente_id': paciente_id,
                'version_id': str(version_id),
                'fecha_snapshot': ultimo_snapshot.fecha,
                'total_nuevos': diagnosticos.count(),
                'diagnosticos_nuevos': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                {'error': f'Error interno: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='por-paciente/(?P<paciente_id>[^/.]+)')
    def por_paciente(self, request, paciente_id=None):
        """
        GET /api/diagnosticos-cie/por-paciente/{paciente_id}/
        
        Retorna todos los diagnósticos de un paciente específico
        """
        try:
            paciente = Paciente.objects.get(id=paciente_id)
        except Paciente.DoesNotExist:
            return Response(
                {'error': 'Paciente no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        diagnosticos = self.get_queryset().filter(
            superficie__diente__paciente=paciente
        )
        
        page = self.paginate_queryset(diagnosticos)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(diagnosticos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request):
        """
        GET /api/diagnosticos-cie/estadisticas/
        
        Retorna estadísticas de diagnósticos:
        - Totales por tipo (presuntivo/definitivo)
        - Distribución por códigos CIE-10
        - Por paciente
        """
        from django.db.models import Count
        
        queryset = self.get_queryset()
        
        # Estadísticas por tipo de diagnóstico
        por_tipo = queryset.values('tipo_diagnostico').annotate(
            total=Count('id')
        ).order_by('tipo_diagnostico')
        
        # Top códigos CIE-10
        top_cie10 = queryset.filter(
            diagnostico_catalogo__codigo_icd10__isnull=False
        ).exclude(
            diagnostico_catalogo__codigo_icd10=''
        ).values(
            'diagnostico_catalogo__codigo_icd10',
            'diagnostico_catalogo__nombre'
        ).annotate(
            total=Count('id')
        ).order_by('-total')[:10]
        
        # Diagnósticos por paciente
        por_paciente = queryset.values(
            'superficie__diente__paciente__nombres',
            'superficie__diente__paciente__apellidos',
            'superficie__diente__paciente_id'
        ).annotate(
            total=Count('id')
        ).order_by('-total')[:10]
        
        return Response({
            'total_diagnosticos': queryset.count(),
            'por_tipo_diagnostico': list(por_tipo),
            'top_codigos_cie10': list(top_cie10),
            'por_paciente': list(por_paciente),
            'fecha_consulta': datetime.now().isoformat()
        })
    
    @action(detail=False, methods=['get'], url_path='codigos-cie10')
    def codigos_cie10(self, request):
        """
        GET /api/diagnosticos-cie/codigos-cie10/
        
        Retorna lista única de códigos CIE-10 utilizados
        """
        from api.odontogram.models import Diagnostico
        
        codigos = Diagnostico.objects.filter(
            activo=True,
            codigo_icd10__isnull=False
        ).exclude(
            codigo_icd10=''
        ).values(
            'codigo_icd10',
            'nombre',
            'siglas'
        ).distinct().order_by('codigo_icd10')
        
        return Response({
            'total_codigos': codigos.count(),
            'codigos': list(codigos)
        })


class DiagnosticoCIEActionsViewSet(viewsets.GenericViewSet):
    """
    ViewSet para acciones sobre diagnósticos CIE-10
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['patch'], url_path='actualizar-tipo')
    def actualizar_tipo(self, request, pk=None):
        """
        PATCH /api/diagnosticos-cie/{id}/actualizar-tipo/
        
        Actualiza el tipo de diagnóstico (presuntivo/definitivo)
        Body: {"tipo_diagnostico": "definitivo"}
        """
        try:
            diagnostico = DiagnosticoDental.objects.get(id=pk, activo=True)
        except DiagnosticoDental.DoesNotExist:
            return Response(
                {'error': 'Diagnóstico no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        tipo_diagnostico = request.data.get('tipo_diagnostico')
        
        if tipo_diagnostico not in ['presuntivo', 'definitivo']:
            return Response(
                {'error': 'tipo_diagnostico debe ser "presuntivo" o "definitivo"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Guardar el tipo original para auditoría
        tipo_original = diagnostico.tipo_diagnostico
        
        # Actualizar el tipo de diagnóstico
        diagnostico.tipo_diagnostico = tipo_diagnostico
        diagnostico.save()
        
        # Registrar en historial
        HistorialOdontograma.objects.create(
            diente=diagnostico.superficie.diente,
            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_MODIFICADO,
            descripcion=f"Diagnóstico marcado como {tipo_diagnostico}",
            odontologo=request.user,
            datos_anteriores={'tipo_diagnostico': tipo_original},
            datos_nuevos={'tipo_diagnostico': tipo_diagnostico}
        )
        
        serializer = DiagnosticoCIESerializer(diagnostico)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='actualizar-multiples')
    def actualizar_multiples(self, request):
        """
        POST /api/diagnosticos-cie/actualizar-multiples/
        
        Actualiza el tipo de diagnóstico para múltiples diagnósticos
        Body: {
            "diagnostico_ids": ["uuid1", "uuid2", ...],
            "tipo_diagnostico": "definitivo"
        }
        """
        diagnostico_ids = request.data.get('diagnostico_ids', [])
        tipo_diagnostico = request.data.get('tipo_diagnostico')
        
        if not diagnostico_ids:
            return Response(
                {'error': 'diagnostico_ids es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if tipo_diagnostico not in ['presuntivo', 'definitivo']:
            return Response(
                {'error': 'tipo_diagnostico debe ser "presuntivo" o "definitivo"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar múltiples diagnósticos
        actualizados = DiagnosticoDental.objects.filter(
            id__in=diagnostico_ids,
            activo=True
        ).update(tipo_diagnostico=tipo_diagnostico)
        
        # Registrar en historial (opcional, batch)
        if actualizados > 0:
            logger.info(f"{actualizados} diagnósticos actualizados a {tipo_diagnostico}")
        
        return Response({
            'success': True,
            'actualizados': actualizados,
            'tipo_diagnostico': tipo_diagnostico
        })