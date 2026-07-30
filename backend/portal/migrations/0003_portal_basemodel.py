from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def migrar_dados(apps, schema_editor):
    AcessoPortalCliente = apps.get_model('portal', 'AcessoPortalCliente')
    now = timezone.now()
    for obj in AcessoPortalCliente.objects.all():
        updates = {
            'is_active': obj.ativo,
            'created_at': obj.criado_em or now,
            'updated_at': now,
        }
        AcessoPortalCliente.objects.filter(pk=obj.pk).update(**updates)
    # registros sem dados (banco vazio): garantir que is_active=True por default ja esta setado


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('portal', '0002_alter_acessoportalcliente_cliente_and_more'),
    ]

    operations = [
        # 1. Adicionar campos BaseModel como nullable/com default para aceitar linhas existentes
        migrations.AddField(
            model_name='acessoportalcliente',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='ativo'),
        ),
        migrations.AddField(
            model_name='acessoportalcliente',
            name='created_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='criado em'),
        ),
        migrations.AddField(
            model_name='acessoportalcliente',
            name='updated_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='atualizado em'),
        ),
        # 2. Migrar dados legados para novos campos
        migrations.RunPython(migrar_dados, migrations.RunPython.noop),
        # 3. Remover campos legados
        migrations.RemoveField(
            model_name='acessoportalcliente',
            name='ativo',
        ),
        migrations.RemoveField(
            model_name='acessoportalcliente',
            name='criado_em',
        ),
    ]
