from django.db import migrations


def crear_metodo(apps, schema_editor):
    MetodoPago = apps.get_model('pagos', 'MetodoPago')
    MetodoPago.objects.get_or_create(
        tipo='cobro_inmediato',
        defaults={
            'nombre': 'Cobro Inmediato',
            'moneda': 'BS',
            'descripcion': 'Débito con OTP — confirmación al instante',
            'requiere_foto_billete': False,
            'activo': True,
            'orden': 0,
        },
    )


def borrar_metodo(apps, schema_editor):
    MetodoPago = apps.get_model('pagos', 'MetodoPago')
    MetodoPago.objects.filter(tipo='cobro_inmediato').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('pagos', '0003_alter_metodopago_tipo'),
    ]
    operations = [
        migrations.RunPython(crear_metodo, borrar_metodo),
    ]
