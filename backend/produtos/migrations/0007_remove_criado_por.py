# Manutencao 62 -- remove o campo legado apos a copia de dados confirmada
# na migration anterior (0006_consolida_criado_por).
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0006_consolida_criado_por'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='combo',
            name='criado_por',
        ),
        migrations.RemoveField(
            model_name='movimentoestoque',
            name='criado_por',
        ),
    ]
