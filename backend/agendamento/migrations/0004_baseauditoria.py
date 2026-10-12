# Manutencao 62 — auditoria BaseModel (created_by/updated_by/deleted_by/deleted_at)
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('agendamento', '0003_agenda_remove_ativo'),
    ]

    operations = [
        migrations.AddField(
            model_name='agenda',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='agenda',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='agenda',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='agenda',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='compromisso',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='compromisso',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='compromisso',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='compromisso',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
    ]
