from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def migrar_historico(apps, schema_editor):
    HistoricoCliente = apps.get_model('clientes', 'HistoricoCliente')
    now = timezone.now()
    for obj in HistoricoCliente.objects.all():
        updates = {
            'created_at': obj.data or now,
            'updated_at': now,
        }
        HistoricoCliente.objects.filter(pk=obj.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clientes', '0002_alter_cliente_nome_razao_social'),
    ]

    operations = [
        # 1. Adicionar campos BaseModel como nullable para aceitar linhas existentes
        migrations.AddField(
            model_name='historicocliente',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='ativo'),
        ),
        migrations.AddField(
            model_name='historicocliente',
            name='created_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='criado em'),
        ),
        migrations.AddField(
            model_name='historicocliente',
            name='updated_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='atualizado em'),
        ),
        # 2. Migrar data -> created_at
        migrations.RunPython(migrar_historico, migrations.RunPython.noop),
        # 3. Remover campo legado
        migrations.RemoveField(
            model_name='historicocliente',
            name='data',
        ),
    ]
