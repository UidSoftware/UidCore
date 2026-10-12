# Manutencao 62 -- copia criado_por_id -> created_by_id (preserva o dado antes
# do RemoveField da migration seguinte). update() em lote, sem disparar signals.
from django.db import migrations
from django.db.models import F


def copiar(apps, schema_editor):
    Cobranca = apps.get_model('pagamentos', 'Cobranca')
    Cobranca.objects.exclude(criado_por_id__isnull=True).update(created_by_id=F('criado_por_id'))


def reverter(apps, schema_editor):
    Cobranca = apps.get_model('pagamentos', 'Cobranca')
    Cobranca.objects.exclude(created_by_id__isnull=True).update(criado_por_id=F('created_by_id'))


class Migration(migrations.Migration):

    dependencies = [
        ('pagamentos', '0004_baseauditoria'),
    ]

    operations = [
        migrations.RunPython(copiar, reverter),
    ]
