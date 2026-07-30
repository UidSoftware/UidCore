from django.db import migrations


def migrar_ativo(apps, schema_editor):
    MetodoPagamento = apps.get_model('pagamentos', 'MetodoPagamento')
    # MetodoPagamento ja herda BaseModel (is_active existe); copiar ativo -> is_active
    MetodoPagamento.objects.filter(ativo=True).update(is_active=True)
    MetodoPagamento.objects.filter(ativo=False).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ('pagamentos', '0002_alter_cobranca_cliente_alter_cobranca_descricao_and_more'),
    ]

    operations = [
        migrations.RunPython(migrar_ativo, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='metodopagamento',
            name='ativo',
        ),
    ]
