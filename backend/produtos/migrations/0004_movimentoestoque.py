# Manutencao 58 — generaliza EntradaEstoque em MovimentoEstoque (RF-01).
# RenameModel preserva os dados existentes (registros antigos recebem
# tipo=ENTRADA via default do campo — todos eram entradas, comportamento
# retroativo correto). related_name muda de 'entradas' para 'movimentos'
# (confirmado via grep que nenhum outro app depende do related_name antigo).

from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('produtos', '0003_combo_itemcombo'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='EntradaEstoque',
            new_name='MovimentoEstoque',
        ),
        migrations.AlterModelTable(
            name='movimentoestoque',
            table='prd_movimento_estoque',
        ),
        migrations.AlterModelOptions(
            name='movimentoestoque',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Movimento de Estoque',
                'verbose_name_plural': 'Movimentos de Estoque',
            },
        ),
        migrations.AddField(
            model_name='movimentoestoque',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('ENTRADA', 'Entrada'),
                    ('ENTRADA_INICIAL', 'Estoque Inicial'),
                    ('DEVOLUCAO_CLIENTE', 'Devolução de Cliente'),
                    ('PERDA', 'Perda/Quebra'),
                    ('AJUSTE', 'Ajuste de Inventário'),
                    ('SAIDA_MANUAL', 'Saída Manual'),
                ],
                default='ENTRADA',
                max_length=20,
                verbose_name='tipo',
            ),
        ),
        migrations.AlterField(
            model_name='movimentoestoque',
            name='produto',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='movimentos',
                to='produtos.produto',
            ),
        ),
        migrations.AlterField(
            model_name='movimentoestoque',
            name='quantidade',
            field=models.DecimalField(
                decimal_places=3, max_digits=12,
                help_text='Pode ser negativa somente quando tipo=AJUSTE.',
                verbose_name='quantidade',
            ),
        ),
        migrations.AlterField(
            model_name='movimentoestoque',
            name='observacoes',
            field=models.TextField(
                blank=True, default='',
                help_text=(
                    'Funciona como "motivo" do movimento — obrigatório '
                    'para todo tipo exceto ENTRADA/ENTRADA_INICIAL (RN-02).'
                ),
                verbose_name='observações',
            ),
        ),
    ]
