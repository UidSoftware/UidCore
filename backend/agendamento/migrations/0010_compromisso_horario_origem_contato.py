"""
Migration 0010 — Manutencao 65 [NUCLEO 4/5]
Adiciona campos de horario, data_horario, origem e contato em Compromisso.
Todos nullable/blank para compatibilidade retroativa total (RN-02).
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('agendamento', '0009_horariodisponivel'),
    ]

    operations = [
        migrations.AddField(
            model_name='compromisso',
            name='horario',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='compromissos',
                to='agendamento.horariodisponivel',
            ),
        ),
        migrations.AddField(
            model_name='compromisso',
            name='data_horario',
            field=models.DateField(
                blank=True, null=True,
                help_text='Data concreta do slot (necessaria pois HorarioDisponivel define dia da semana, nao data absoluta).',
            ),
        ),
        migrations.AddField(
            model_name='compromisso',
            name='origem',
            field=models.CharField(
                choices=[('INTERNO', 'Interno'), ('PUBLICO', 'Público')],
                default='INTERNO',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='compromisso',
            name='nome_contato',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='compromisso',
            name='telefone_contato',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='compromisso',
            name='email_contato',
            field=models.EmailField(blank=True),
        ),
    ]
