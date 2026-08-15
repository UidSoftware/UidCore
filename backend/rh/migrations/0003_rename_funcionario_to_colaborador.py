# Manutencao #33 — Renomeia Funcionario → Colaborador em todo o app rh.
#
# Operacoes de banco:
#   1. RenameModel   Funcionario → Colaborador
#   2. AlterModelTable colaborador → rh_colaborador  (db_table explicito)
#   3. AlterField colaborador.cargo → related_name='colaboradores'
#   4. RenameField folhapagamento.funcionario → colaborador  (coluna funcionario_id → colaborador_id)
#   5. RenameField registroferias.funcionario → colaborador  (coluna funcionario_id → colaborador_id)
#
# Sem perda de dados — tudo e rename de tabela/coluna no PostgreSQL.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0002_alter_cargo_nome_alter_folhapagamento_funcionario_and_more'),
    ]

    operations = [
        # 1. Renomeia o model (estado do ORM)
        migrations.RenameModel(
            old_name='Funcionario',
            new_name='Colaborador',
        ),
        # 2. Renomeia a tabela no banco (db_table explicito muda de rh_funcionario → rh_colaborador)
        migrations.AlterModelTable(
            name='colaborador',
            table='rh_colaborador',
        ),
        # 3. Atualiza related_name no FK cargo (funcionarios → colaboradores)
        migrations.AlterField(
            model_name='colaborador',
            name='cargo',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='colaboradores',
                to='rh.cargo',
            ),
        ),
        # 4. Renomeia coluna funcionario_id → colaborador_id em FolhaPagamento
        migrations.RenameField(
            model_name='folhapagamento',
            old_name='funcionario',
            new_name='colaborador',
        ),
        # 5. Renomeia coluna funcionario_id → colaborador_id em RegistroFerias
        migrations.RenameField(
            model_name='registroferias',
            old_name='funcionario',
            new_name='colaborador',
        ),
    ]
