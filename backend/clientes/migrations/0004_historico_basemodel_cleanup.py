import django.utils.timezone
from django.db import migrations, models


def preencher_created_at(apps, schema_editor):
    """Garante que nenhuma linha tem created_at/updated_at NULL antes do AlterField."""
    HistoricoCliente = apps.get_model('clientes', 'HistoricoCliente')
    now = django.utils.timezone.now()
    HistoricoCliente.objects.filter(created_at__isnull=True).update(created_at=now)
    HistoricoCliente.objects.filter(updated_at__isnull=True).update(updated_at=now)


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0003_historico_cliente_basemodel'),
    ]

    operations = [
        migrations.RunPython(preencher_created_at, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='historicocliente',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Histórico',
                'verbose_name_plural': 'Históricos',
            },
        ),
        migrations.AlterField(
            model_name='historicocliente',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='criado em'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='historicocliente',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='atualizado em'),
        ),
    ]
