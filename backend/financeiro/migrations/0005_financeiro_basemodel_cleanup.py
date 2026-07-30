import django.utils.timezone
from django.db import migrations, models


def preencher_timestamps(apps, schema_editor):
    """Garante que nenhuma linha tem created_at/updated_at NULL antes do AlterField."""
    now = django.utils.timezone.now()
    ItemConciliacao = apps.get_model('financeiro', 'ItemConciliacao')
    ItemConciliacao.objects.filter(created_at__isnull=True).update(created_at=now)
    ItemConciliacao.objects.filter(updated_at__isnull=True).update(updated_at=now)
    PadraoSeguroConciliacao = apps.get_model('financeiro', 'PadraoSeguroConciliacao')
    PadraoSeguroConciliacao.objects.filter(created_at__isnull=True).update(created_at=now)
    PadraoSeguroConciliacao.objects.filter(updated_at__isnull=True).update(updated_at=now)


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0004_financeiro_basemodel'),
    ]

    operations = [
        migrations.RunPython(preencher_timestamps, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='itemconciliacao',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='criado em'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='itemconciliacao',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='atualizado em'),
        ),
        migrations.AlterField(
            model_name='padraoseguroconciliacao',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='criado em'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='padraoseguroconciliacao',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='atualizado em'),
        ),
    ]
