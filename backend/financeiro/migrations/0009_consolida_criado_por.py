# Manutencao 62 — copia criado_por_id -> created_by_id por model afetado
# (preserva o dado antes do RemoveField da migration seguinte). update() em
# lote por model, nao save() por linha — evita disparar signals indevidos
# (RN da secao 2/Risco medio da Especificacao Hotfix: cada RunPython isolado
# por model, se um falhar os demais ja aplicados nesta mesma migration nao
# sao desfeitos individualmente, mas a migration inteira roda em uma unica
# transacao do Postgres via atomic, entao falha integral reverte tudo).
from django.db import migrations
from django.db.models import F

MODELOS = [
    'Aporte', 'ConciliacaoExtrato', 'Conta', 'Despesa',
    'EstornoReceita', 'PadraoSeguroConciliacao', 'Receita',
]


def copiar(apps, schema_editor):
    for nome in MODELOS:
        Model = apps.get_model('financeiro', nome)
        Model.objects.exclude(criado_por_id__isnull=True).update(created_by_id=F('criado_por_id'))


def reverter(apps, schema_editor):
    for nome in MODELOS:
        Model = apps.get_model('financeiro', nome)
        Model.objects.exclude(created_by_id__isnull=True).update(criado_por_id=F('created_by_id'))


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0008_baseauditoria'),
    ]

    operations = [
        migrations.RunPython(copiar, reverter),
    ]
