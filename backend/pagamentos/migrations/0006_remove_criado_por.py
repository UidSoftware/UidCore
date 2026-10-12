# Manutencao 62 -- remove o campo legado apos a copia de dados confirmada
# na migration anterior (0005_consolida_criado_por).
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pagamentos', '0005_consolida_criado_por'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cobranca',
            name='criado_por',
        ),
    ]
