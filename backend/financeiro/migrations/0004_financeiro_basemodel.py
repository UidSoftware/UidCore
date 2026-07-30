from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def migrar_padrao_seguro(apps, schema_editor):
    PadraoSeguroConciliacao = apps.get_model('financeiro', 'PadraoSeguroConciliacao')
    now = timezone.now()
    for obj in PadraoSeguroConciliacao.objects.all():
        updates = {
            'is_active': obj.ativo,
            'created_at': obj.criado_em or now,
            'updated_at': now,
        }
        PadraoSeguroConciliacao.objects.filter(pk=obj.pk).update(**updates)


def migrar_item_conciliacao(apps, schema_editor):
    # ItemConciliacao nao tinha campos legados para migrar — so adicionar is_active/created_at/updated_at
    # RunPython nao e necessario mas mantemos para consistencia de padrao
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('financeiro', '0003_alter_aporte_data_alter_aporte_descricao_and_more'),
    ]

    operations = [
        # --- PadraoSeguroConciliacao: Models.Model -> BaseModel ---
        # 1. Adicionar campos BaseModel
        migrations.AddField(
            model_name='padraoseguroconciliacao',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='ativo'),
        ),
        migrations.AddField(
            model_name='padraoseguroconciliacao',
            name='created_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='criado em'),
        ),
        migrations.AddField(
            model_name='padraoseguroconciliacao',
            name='updated_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='atualizado em'),
        ),
        # 2. Migrar dados (ativo->is_active, criado_em->created_at)
        migrations.RunPython(migrar_padrao_seguro, migrations.RunPython.noop),
        # 3. Remover campos legados
        migrations.RemoveField(
            model_name='padraoseguroconciliacao',
            name='ativo',
        ),
        migrations.RemoveField(
            model_name='padraoseguroconciliacao',
            name='criado_em',
        ),

        # --- ItemConciliacao: models.Model -> BaseModel ---
        # Nao ha campos legados para migrar; apenas adicionar os campos do BaseModel
        migrations.AddField(
            model_name='itemconciliacao',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='ativo'),
        ),
        migrations.AddField(
            model_name='itemconciliacao',
            name='created_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='criado em'),
        ),
        migrations.AddField(
            model_name='itemconciliacao',
            name='updated_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name='atualizado em'),
        ),
        migrations.RunPython(migrar_item_conciliacao, migrations.RunPython.noop),
    ]
