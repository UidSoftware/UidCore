from django.db import migrations


def migrar_ativo(apps, schema_editor):
    Agenda = apps.get_model('agendamento', 'Agenda')
    # Agenda ja herda BaseModel (is_active existe); copiar ativo -> is_active
    Agenda.objects.filter(ativo=True).update(is_active=True)
    Agenda.objects.filter(ativo=False).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ('agendamento', '0002_alter_agenda_nome_alter_compromisso_agenda_and_more'),
    ]

    operations = [
        migrations.RunPython(migrar_ativo, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='agenda',
            name='ativo',
        ),
    ]
