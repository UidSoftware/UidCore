"""
Migration RunPython: copia campo 'documento' para 'cpf' (len=11) ou 'cnpj' (len=14)
em todos os registros de fornecedores existentes.
"""
from django.db import migrations


def copiar_documento_fornecedores(apps, schema_editor):
    Fornecedor = apps.get_model('fornecedores', 'Fornecedor')
    for fornecedor in Fornecedor.objects.exclude(documento__isnull=True).exclude(documento=''):
        doc = fornecedor.documento or ''
        if len(doc) == 11:
            fornecedor.cpf = doc
            fornecedor.save(update_fields=['cpf'])
        elif len(doc) == 14:
            fornecedor.cnpj = doc
            fornecedor.save(update_fields=['cnpj'])


def reverter(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('fornecedores', '0003_fornecedor_cnpj_fornecedor_cpf_acionistafornecedor'),
    ]

    operations = [
        migrations.RunPython(copiar_documento_fornecedores, reverter),
    ]
