# Manutencao 62 — remove os campos legados apos a copia de dados confirmada
# na migration anterior (0009_consolida_criado_por).
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0009_consolida_criado_por'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='aporte',
            name='criado_por',
        ),
        migrations.RemoveField(
            model_name='conciliacaoextrato',
            name='criado_por',
        ),
        migrations.RemoveField(
            model_name='conta',
            name='criado_por',
        ),
        migrations.RemoveField(
            model_name='despesa',
            name='criado_por',
        ),
        migrations.RemoveField(
            model_name='estornoreceita',
            name='criado_por',
        ),
        migrations.RemoveField(
            model_name='padraoseguroconciliacao',
            name='criado_por',
        ),
        migrations.RemoveField(
            model_name='receita',
            name='criado_por',
        ),
    ]
