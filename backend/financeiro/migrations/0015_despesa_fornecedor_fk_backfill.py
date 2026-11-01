from django.db import migrations


def backfill_fornecedor_fk(apps, schema_editor):
    """
    RF-02/RN-02 (Manutencao 89): para cada Despesa com fornecedor_fk nulo
    e texto `fornecedor` nao vazio, tenta um match exato (case-insensitive,
    strip) com Fornecedor.nome_razao_social. So vincula em caso de
    exatamente 1 resultado ativo — ambiguo (2+) ou sem match (0) nao
    altera nada, o texto legado permanece intacto. Idempotente: rodar de
    novo nao muda nada (despesas ja vinculadas sao ignoradas pelo filtro
    fornecedor_fk__isnull=True).
    """
    Despesa = apps.get_model('financeiro', 'Despesa')
    Fornecedor = apps.get_model('fornecedores', 'Fornecedor')

    qs = Despesa.objects.filter(fornecedor_fk__isnull=True).exclude(fornecedor='')
    for despesa in qs.iterator():
        nome = (despesa.fornecedor or '').strip()
        if not nome:
            continue
        candidatos = list(
            Fornecedor.objects.filter(
                nome_razao_social__iexact=nome, is_active=True,
            ).values_list('id', flat=True)[:2]
        )
        if len(candidatos) == 1:
            despesa.fornecedor_fk_id = candidatos[0]
            despesa.save(update_fields=['fornecedor_fk'])
        # 0 ou 2+ candidatos: ambiguo/sem match, nao altera (RN-02).


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0014_despesa_fornecedor_fk'),
    ]

    operations = [
        migrations.RunPython(
            backfill_fornecedor_fk, migrations.RunPython.noop, atomic=True,
        ),
    ]
