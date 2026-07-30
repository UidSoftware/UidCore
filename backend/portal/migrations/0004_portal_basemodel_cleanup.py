import django.utils.timezone
from django.db import migrations, models


def preencher_timestamps(apps, schema_editor):
    """Garante que nenhuma linha tem created_at/updated_at NULL antes do AlterField."""
    AcessoPortalCliente = apps.get_model('portal', 'AcessoPortalCliente')
    now = django.utils.timezone.now()
    AcessoPortalCliente.objects.filter(created_at__isnull=True).update(created_at=now)
    AcessoPortalCliente.objects.filter(updated_at__isnull=True).update(updated_at=now)


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0003_portal_basemodel'),
    ]

    operations = [
        migrations.RunPython(preencher_timestamps, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='acessoportalcliente',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='criado em'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='acessoportalcliente',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='atualizado em'),
        ),
    ]
