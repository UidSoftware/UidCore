"""
Migration 0013 — Manutencao 92 [RF-01, passo 3/3]

Remove o campo antigo `profissional` (FK para accounts.User, ja sem uso
depois do backfill da migration 0012) e renomeia o campo novo
`profissional_colaborador` para `profissional` -- estado final bate
exatamente com agendamento/models.py (FK para rh.Colaborador,
related_name='agendas_vinculadas', limit_choices_to is_active=True).
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('agendamento', '0012_migra_profissional_para_colaborador'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='agenda',
            name='profissional',
        ),
        migrations.RenameField(
            model_name='agenda',
            old_name='profissional_colaborador',
            new_name='profissional',
        ),
        migrations.AlterField(
            model_name='agenda',
            name='profissional',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='agendas_vinculadas',
                to='rh.colaborador',
                verbose_name='profissional responsável',
                limit_choices_to={'is_active': True},
            ),
        ),
    ]
