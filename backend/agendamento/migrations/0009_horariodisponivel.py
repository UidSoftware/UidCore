"""
Migration 0009 — Manutencao 65 [NUCLEO 4/5]
Cria a tabela age_horario_disponivel.
"""
from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('agendamento', '0008_agenda_slug_publico'),
    ]

    operations = [
        migrations.CreateModel(
            name='HorarioDisponivel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('is_active', models.BooleanField(default=True, verbose_name='ativo')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='excluído em')),
                ('dia_semana', models.IntegerField(
                    choices=[(0, 'Segunda'), (1, 'Terça'), (2, 'Quarta'), (3, 'Quinta'),
                             (4, 'Sexta'), (5, 'Sábado'), (6, 'Domingo')],
                )),
                ('hora_inicio', models.TimeField()),
                ('duracao_minutos', models.PositiveIntegerField(
                    validators=[django.core.validators.MinValueValidator(5)],
                )),
                ('vagas', models.PositiveIntegerField(
                    validators=[django.core.validators.MinValueValidator(1)],
                )),
                ('servico', models.CharField(blank=True, max_length=255)),
                ('publico', models.BooleanField(default=True)),
                ('ativo', models.BooleanField(
                    default=True,
                    help_text='Indica se este horário está sendo ofertado. Distinto do is_active (soft delete).',
                )),
                ('agenda', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='horarios',
                    to='agendamento.agenda',
                )),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='criado por',
                )),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='atualizado por',
                )),
                ('deleted_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='excluído por',
                )),
            ],
            options={
                'db_table': 'age_horario_disponivel',
                'ordering': ['dia_semana', 'hora_inicio'],
            },
        ),
    ]
