"""
Migration 0014 — Manutencao 92 (RF-14, opcional)
Adiciona campo `canal` em Compromisso. AddField simples, sem RunPython --
default '' cobre todos os registros existentes.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agendamento', '0013_agenda_remove_profissional_rename'),
    ]

    operations = [
        migrations.AddField(
            model_name='compromisso',
            name='canal',
            field=models.CharField(
                blank=True,
                choices=[('SITE', 'Site'), ('INSTAGRAM', 'Instagram'), ('WHATSAPP', 'WhatsApp'), ('OUTRO', 'Outro')],
                default='',
                max_length=10,
            ),
        ),
    ]
