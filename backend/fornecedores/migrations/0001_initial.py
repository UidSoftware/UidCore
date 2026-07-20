import common.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Fornecedor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('is_active', models.BooleanField(default=True, verbose_name='ativo')),
                ('tipo_pessoa', models.CharField(choices=[('PF', 'Pessoa Física'), ('PJ', 'Pessoa Jurídica')], default='PJ', max_length=2, verbose_name='tipo de pessoa')),
                ('documento', models.CharField(blank=True, help_text='Apenas dígitos (sem máscara)', max_length=14, null=True, unique=True, validators=[common.validators.validar_documento], verbose_name='CPF/CNPJ')),
                ('nome_razao_social', models.CharField(max_length=255, verbose_name='nome / razão social')),
                ('telefone', models.CharField(blank=True, max_length=20, verbose_name='telefone')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='e-mail')),
                ('endereco', models.CharField(blank=True, max_length=255, verbose_name='endereço')),
                ('cidade', models.CharField(blank=True, max_length=100, verbose_name='cidade')),
                ('estado', models.CharField(blank=True, choices=[('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'), ('BA', 'BA'), ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'), ('GO', 'GO'), ('MA', 'MA'), ('MT', 'MT'), ('MS', 'MS'), ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'), ('PR', 'PR'), ('PE', 'PE'), ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'), ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), ('SC', 'SC'), ('SP', 'SP'), ('SE', 'SE'), ('TO', 'TO')], max_length=2, verbose_name='estado')),
                ('cep', models.CharField(blank=True, max_length=8, verbose_name='CEP')),
                ('observacoes', models.TextField(blank=True, verbose_name='observações')),
                ('categoria', models.CharField(choices=[('MATERIA_PRIMA', 'Matéria Prima'), ('SERVICOS', 'Serviços'), ('TECNOLOGIA', 'Tecnologia'), ('LOGISTICA', 'Logística'), ('MANUTENCAO', 'Manutenção'), ('ESCRITORIO', 'Material de Escritório'), ('MARKETING', 'Marketing'), ('OUTRO', 'Outro')], default='OUTRO', max_length=20, verbose_name='categoria')),
                ('contato_nome', models.CharField(blank=True, max_length=150, verbose_name='nome do contato')),
                ('contato_telefone', models.CharField(blank=True, max_length=20, verbose_name='telefone do contato')),
                ('website', models.URLField(blank=True, verbose_name='website')),
                ('inscricao_estadual', models.CharField(blank=True, max_length=20, verbose_name='inscrição estadual')),
            ],
            options={
                'verbose_name': 'Fornecedor',
                'verbose_name_plural': 'Fornecedores',
                'db_table': 'fornecedores_fornecedor',
                'ordering': ['-created_at'],
            },
        ),
    ]
