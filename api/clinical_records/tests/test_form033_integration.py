# test_form033_integration.py (crear en la raíz del proyecto o en tests/)

"""
Script de prueba para la integración Form033 con Historial Clínico
"""

def test_integration():
    """
    Prueba la integración completa
    """
    print("=" * 60)
    print("PRUEBA DE INTEGRACIÓN: Form033 + Historial Clínico")
    print("=" * 60)
    
    # Test 1: Verificar que el modelo existe
    try:
        from api.clinical_records.models import Form033Snapshot
        print("✅ Modelo Form033Snapshot importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando modelo: {e}")
        return
    
    # Test 2: Verificar serializers
    try:
        from api.clinical_records.serializers.form033_snapshot_serializer import (
            Form033SnapshotSerializer,
            Form033SnapshotCreateSerializer
        )
        print("✅ Serializers importados correctamente")
    except ImportError as e:
        print(f"❌ Error importando serializers: {e}")
        return
    
    # Test 3: Verificar servicio
    try:
        from api.clinical_records.services.form033_storage_service import Form033StorageService
        print("✅ Servicio Form033StorageService importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando servicio: {e}")
        return
    
    # Test 4: Verificar método en ClinicalRecordService
    try:
        from api.clinical_records.services.clinical_record_service import ClinicalRecordService
        assert hasattr(ClinicalRecordService, 'agregar_form033_a_historial')
        print("✅ Método agregar_form033_a_historial existe en ClinicalRecordService")
    except (ImportError, AssertionError) as e:
        print(f"❌ Error verificando ClinicalRecordService: {e}")
        return
    
    # Test 5: Verificar endpoints en ViewSet
    try:
        from api.clinical_records.views.clinical_record_viewset import ClinicalRecordViewSet
        assert hasattr(ClinicalRecordViewSet, 'agregar_form033')
        assert hasattr(ClinicalRecordViewSet, 'obtener_form033')
        assert hasattr(ClinicalRecordViewSet, 'eliminar_form033')
        print("✅ Endpoints de Form033 existen en ClinicalRecordViewSet")
    except (ImportError, AssertionError) as e:
        print(f"❌ Error verificando ViewSet: {e}")
        return
    
    # Test 6: Verificar estructura de la tabla en DB
    try:
        count = Form033Snapshot.objects.count()
        print(f"✅ Tabla Form033Snapshot existe en la BD (registros: {count})")
    except Exception as e:
        print(f"❌ Error accediendo a la tabla: {e}")
        return
    
    print("\n" + "=" * 60)
    print("🎉 TODOS LOS TESTS PASARON CORRECTAMENTE")
    print("=" * 60)
    print("\nEndpoints disponibles:")
    print("  POST   /api/clinical-records/{id}/agregar-form033/")
    print("  GET    /api/clinical-records/{id}/obtener-form033/")
    print("  DELETE /api/clinical-records/{id}/eliminar-form033/")
    print("\n")


if __name__ == '__main__':
    import django
    import os
    
    # Configurar Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    test_integration()
