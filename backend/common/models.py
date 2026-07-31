from django.db import models
from .validators import validar_documento


UF_CHOICES = [
    ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'),
    ('BA', 'BA'), ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'),
    ('GO', 'GO'), ('MA', 'MA'), ('MT', 'MT'), ('MS', 'MS'),
    ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'), ('PR', 'PR'),
    ('PE', 'PE'), ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'),
    ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), ('SC', 'SC'),
    ('SP', 'SP'), ('SE', 'SE'), ('TO', 'TO'),
]


class BaseModel(models.Model):
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)
    is_active = models.BooleanField('ativo', default=True)

    class Meta:
        abstract = True


class TipoPessoa(models.TextChoices):
    PF = 'PF', 'Pessoa Física'
    PJ = 'PJ', 'Pessoa Jurídica'


class PessoaBase(BaseModel):
    tipo_pessoa = models.CharField(
        'tipo de pessoa', max_length=2,
        choices=TipoPessoa.choices, default=TipoPessoa.PJ,
    )
    documento = models.CharField(
        'CPF/CNPJ', max_length=14,
        unique=True, null=True, blank=True,
        validators=[validar_documento],
        help_text='Apenas dígitos (sem máscara)',
    )
    cpf = models.CharField(
        'CPF', max_length=11, blank=True, default='',
        help_text='Apenas dígitos (11 caracteres)',
    )
    cnpj = models.CharField(
        'CNPJ', max_length=14, blank=True, default='',
        help_text='Apenas dígitos (14 caracteres)',
    )
    nome_razao_social = models.CharField('nome / razão social', max_length=255, blank=True)
    telefone = models.CharField('telefone', max_length=20, blank=True)
    email = models.EmailField('e-mail', blank=True)
    endereco = models.CharField('endereço', max_length=255, blank=True)
    cidade = models.CharField('cidade', max_length=100, blank=True)
    estado = models.CharField('estado', max_length=2, choices=UF_CHOICES, blank=True)
    cep = models.CharField('CEP', max_length=8, blank=True)
    observacoes = models.TextField('observações', blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.nome_razao_social
