"""
Migration 0008 — Manutencao 65 [NUCLEO 4/5]
Adiciona slug e permite_agendamento_publico em Agenda.

Estrategia: todo o DDL via RunSQL para controle total.
- SeparateDatabaseAndState sincroniza o estado Django sem gerar DDL automatico.
- Isso evita que Django crie o indice varchar_pattern_ops duplicado.
"""
from django.db import migrations, models
from django.utils.text import slugify


def _popular_slugs(apps, schema_editor):
    Agenda = apps.get_model('agendamento', 'Agenda')
    usados = set()
    for agenda in Agenda.objects.all().order_by('id'):
        if agenda.slug:
            usados.add(agenda.slug)
            continue
        base = slugify(agenda.nome or f'agenda-{agenda.pk}') or f'agenda-{agenda.pk}'
        slug = base
        n = 1
        while slug in usados:
            slug = f'{base}-{n}'
            n += 1
        agenda.slug = slug
        agenda.save(update_fields=['slug'])
        usados.add(slug)


class Migration(migrations.Migration):

    dependencies = [
        ('agendamento', '0007_agenda_profissional'),
    ]

    operations = [
        # 1. DDL: adiciona coluna slug e coluna permite_agendamento_publico
        #    SeparateDatabaseAndState: DDL no banco + estado Django em sincronia
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE age_agenda
                        ADD COLUMN IF NOT EXISTS slug varchar(100) DEFAULT '' NOT NULL;
                    """,
                    reverse_sql="ALTER TABLE age_agenda DROP COLUMN IF EXISTS slug;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='agenda',
                    name='slug',
                    field=models.SlugField(
                        blank=True, max_length=100,
                        help_text='Identificador unico para URL publica.',
                    ),
                ),
            ],
        ),
        # 2. Adiciona permite_agendamento_publico diretamente (BooleanField com default nao gera indice)
        migrations.AddField(
            model_name='agenda',
            name='permite_agendamento_publico',
            field=models.BooleanField(default=False, verbose_name='permite agendamento público'),
        ),
        # 3. Popula slugs para registros existentes
        migrations.RunPython(_popular_slugs, migrations.RunPython.noop),
        # 4. Adiciona unique constraint + indice LIKE via SQL idempotente
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'age_agenda_slug_key'
                          AND conrelid = 'age_agenda'::regclass
                    ) THEN
                        ALTER TABLE age_agenda ADD CONSTRAINT age_agenda_slug_key UNIQUE (slug);
                    END IF;
                END $$;

                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes
                        WHERE indexname = 'age_agenda_slug_85866b91_like'
                    ) THEN
                        CREATE INDEX age_agenda_slug_85866b91_like
                        ON age_agenda (slug varchar_pattern_ops);
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'age_agenda_slug_key') THEN
                        ALTER TABLE age_agenda DROP CONSTRAINT age_agenda_slug_key;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'age_agenda_slug_85866b91_like') THEN
                        DROP INDEX age_agenda_slug_85866b91_like;
                    END IF;
                END $$;
            """,
        ),
        # 5. Sincroniza estado Django para SlugField unique=True (sem DDL — banco ja tem)
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='agenda',
                    name='slug',
                    field=models.SlugField(
                        blank=True, max_length=100, unique=True,
                        help_text='Identificador unico para URL publica. Gerado automaticamente a partir do nome.',
                    ),
                ),
            ],
        ),
    ]
