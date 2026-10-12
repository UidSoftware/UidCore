# Manutencao 63 [NUCLEO 2/5] (RF-01) — adiciona FINANCEIRO e PROFISSIONAL
# aos choices de PerfilUsuario. Sem RunPython: perfil novo e opt-in via
# tela Usuarios, ninguem e promovido automaticamente (RN-01/RN-02 da
# Especificacao_Hotfix.md intactos — User.tem_acesso_total nao muda).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_seed_superadmin_perfil'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='perfil',
            field=models.CharField(choices=[('ADMIN', 'Admin'), ('OPERACIONAL', 'Operacional'), ('MARKETING', 'Marketing'), ('SUPERADMIN', 'Superadmin'), ('FINANCEIRO', 'Financeiro'), ('PROFISSIONAL', 'Profissional')], default='OPERACIONAL', max_length=12, verbose_name='perfil'),
        ),
    ]
