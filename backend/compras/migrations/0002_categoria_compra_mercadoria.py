# RF-09 (Manutencao 58, Fase 2): seed idempotente da Categoria financeira
# usada pelo signal compra_sincroniza_despesa (compras/signals.py). Primeira
# RunPython de seed de dado do projeto — evita depender de fixture manual ou
# de alguém criar a categoria certa via admin antes do primeiro uso. get_or_
# create garante que rodar `migrate` duas vezes não duplica a Categoria (CA-18).
from django.db import migrations


def criar_categoria_compra_mercadoria(apps, schema_editor):
    Categoria = apps.get_model('financeiro', 'Categoria')
    Categoria.objects.get_or_create(
        nome='Compra de Mercadoria', tipo='SAIDA',
        defaults={'is_active': True},
    )


def remover_categoria_compra_mercadoria(apps, schema_editor):
    Categoria = apps.get_model('financeiro', 'Categoria')
    Categoria.objects.filter(nome='Compra de Mercadoria', tipo='SAIDA').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0001_initial'),
        ('financeiro', '0007_estornoreceita_item_venda_estornoreceita_receita'),
    ]

    operations = [
        migrations.RunPython(
            criar_categoria_compra_mercadoria,
            reverse_code=remover_categoria_compra_mercadoria,
        ),
    ]
