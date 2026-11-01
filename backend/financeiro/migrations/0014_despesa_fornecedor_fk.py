import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fornecedores', '0005_baseauditoria'),
        ('financeiro', '0013_categoria_pai'),
    ]

    operations = [
        migrations.AddField(
            model_name='despesa',
            name='fornecedor_fk',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='despesas', to='fornecedores.fornecedor',
            ),
        ),
        migrations.AddField(
            model_name='despesa',
            name='subcategoria',
            field=models.ForeignKey(
                blank=True, null=True,
                limit_choices_to={'is_active': True, 'tipo': 'SAIDA'},
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='despesas_subcategoria', to='financeiro.categoria',
            ),
        ),
        migrations.AddField(
            model_name='despesa',
            name='tipo_desconto',
            field=models.CharField(
                choices=[('R$', 'Valor fixo (R$)'), ('%', 'Percentual (%)')],
                default='R$', max_length=2,
            ),
        ),
        migrations.AddField(
            model_name='despesa',
            name='percentual_desconto',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]
