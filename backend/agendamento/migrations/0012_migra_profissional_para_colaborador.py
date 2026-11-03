"""
Migration 0012 — Manutencao 92 [RF-01/RF-02, passo 2/3]

RunPython: para cada Agenda com `profissional_id` (User, campo antigo)
preenchido, busca o rh.Colaborador correspondente (via Colaborador.usuario)
e grava no campo novo `profissional_colaborador`. Agenda sem Colaborador
correspondente (ex.: User administrativo sem Colaborador, ou Colaborador
inativo) fica com o campo novo vazio -- NUNCA falha a migration por isso
(RN-03), so reporta via print() (aparece no log do `migrate`, e o Sentinel
confere esse relatorio explicitamente -- CA-03/CA-10).

Reversa e no-op: e migracao de dado derivado (o campo antigo continua
intacto nesta migration), nao ha nada de primario pra desfazer aqui.
"""
from django.db import migrations


def migrar(apps, schema_editor):
    Agenda = apps.get_model('agendamento', 'Agenda')
    Colaborador = apps.get_model('rh', 'Colaborador')

    sem_match = []
    migradas = 0
    for agenda in Agenda.objects.filter(profissional_id__isnull=False):
        colaborador = Colaborador.objects.filter(
            usuario_id=agenda.profissional_id, is_active=True,
        ).first()
        if colaborador:
            agenda.profissional_colaborador = colaborador
            agenda.save(update_fields=['profissional_colaborador'])
            migradas += 1
        else:
            sem_match.append(f'Agenda#{agenda.id} ({agenda.nome})')

    if sem_match:
        print(
            f'[Manutencao 92] {len(sem_match)} agenda(s) sem Colaborador '
            f'correspondente, profissional ficou vazio: {", ".join(sem_match)}'
        )
    else:
        print(f'[Manutencao 92] {migradas} agenda(s) migradas; 0 agendas sem profissional correspondente.')


class Migration(migrations.Migration):

    dependencies = [
        ('agendamento', '0011_agenda_profissional_colaborador'),
    ]

    operations = [
        migrations.RunPython(migrar, migrations.RunPython.noop),
    ]
