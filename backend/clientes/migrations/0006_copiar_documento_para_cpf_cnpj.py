"""
Migration RunPython: copia campo 'documento' para 'cpf' (len=11) ou 'cnpj' (len=14)
em todos os registros de clientes existentes.
"""
from django.db import migrations


def copiar_documento_clientes(apps, schema_editor):
    Cliente = apps.get_model('clientes', 'Cliente')
    for cliente in Cliente.objects.exclude(documento__isnull=True).exclude(documento=''):
        doc = cliente.documento or ''
        if len(doc) == 11:
            cliente.cpf = doc
            cliente.save(update_fields=['cpf'])
        elif len(doc) == 14:
            cliente.cnpj = doc
            cliente.save(update_fields=['cnpj'])


def reverter(apps, schema_editor):
    # Reversao inócua: os campos cpf/cnpj serao zerados na migration anterior
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0005_cliente_cnpj_cliente_cpf_acionistacliente'),
    ]

    operations = [
        migrations.RunPython(copiar_documento_clientes, reverter),
    ]
