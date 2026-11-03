"""
Migration 0011 — Manutencao 92 [RF-01, passo 1/3]

Adiciona o campo NOVO `profissional_colaborador` (FK para rh.Colaborador),
SEM tocar no campo antigo `profissional` (FK para accounts.User). As duas
colunas convivem lado a lado ate a migration 0013, que remove a antiga e
renomeia esta pra `profissional` -- o backfill de dado (migration 0012)
roda no meio, com as duas colunas presentes, pra nunca perder informacao
(RN-03: migracao de dados nao-destrutiva por design).
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('agendamento', '0010_compromisso_horario_origem_contato'),
        ('rh', '0005_baseauditoria'),
    ]

    operations = [
        migrations.AddField(
            model_name='agenda',
            name='profissional_colaborador',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='agendas_vinculadas_novo',
                to='rh.colaborador',
                verbose_name='profissional responsável',
            ),
        ),
    ]
