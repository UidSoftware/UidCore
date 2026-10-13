from django.conf import settings
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


class BaseModelManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)
    is_active = models.BooleanField('ativo', default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='criado por',
        null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='atualizado por',
        null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='excluído por',
        null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    deleted_at = models.DateTimeField('excluído em', null=True, blank=True)

    objects = BaseModelManager()
    all_objects = models.Manager()

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


class FormatoExportacao(models.TextChoices):
    JSON = 'JSON', 'JSON'
    PDF = 'PDF', 'PDF'


class ExportacaoTitular(BaseModel):
    """
    Manutencao #66 [NUCLEO 5/5] — trilha de auditoria da exportação de
    dados do titular (LGPD art. 18). Toda exportação (JSON ou PDF) grava um
    registro aqui ANTES de devolver a resposta — é o "backup" que a
    anonimização exige existir previamente (RN-02 da Especificacao_Hotfix).
    `created_by`/`created_at` (herdados de BaseModel) já respondem "quem
    exportou e quando" — sem campo duplicado. Nunca editável depois de
    criado (sem endpoint de update/delete).
    """
    cliente = models.ForeignKey(
        'clientes.Cliente', verbose_name='cliente',
        on_delete=models.PROTECT, related_name='exportacoes_lgpd',
    )
    formato = models.CharField(
        'formato', max_length=4, choices=FormatoExportacao.choices,
    )
    conteudo_resumo = models.TextField('resumo do conteúdo', blank=True, default='')

    class Meta:
        db_table = 'common_exportacao_titular'
        ordering = ['-created_at']
        verbose_name = 'Exportação de Titular (LGPD)'
        verbose_name_plural = 'Exportações de Titular (LGPD)'

    def __str__(self):
        return f'{self.cliente} — {self.formato} — {self.created_at:%d/%m/%Y %H:%M}'
