from django.db import models
from common.models import BaseModel, PessoaBase
from django.db import transaction


class SegmentoCliente(models.TextChoices):
    COMERCIO = 'COMERCIO', 'Comércio'
    SERVICOS = 'SERVICOS', 'Serviços'
    INDUSTRIA = 'INDUSTRIA', 'Indústria'
    SAUDE = 'SAUDE', 'Saúde'
    EDUCACAO = 'EDUCACAO', 'Educação'
    TECNOLOGIA = 'TECNOLOGIA', 'Tecnologia'
    ALIMENTACAO = 'ALIMENTACAO', 'Alimentação'
    OUTRO = 'OUTRO', 'Outro'


class Cliente(PessoaBase):
    segmento = models.CharField(
        'segmento', max_length=20,
        choices=SegmentoCliente.choices, default=SegmentoCliente.OUTRO,
    )
    data_nascimento = models.DateField('data de nascimento', null=True, blank=True)
    origem = models.CharField('origem', max_length=100, blank=True,
                              help_text='Como o cliente chegou (indicação, Google, etc.)')
    limite_credito = models.DecimalField(
        'limite de crédito', max_digits=12, decimal_places=2, default=0,
    )

    class Meta:
        db_table = 'clientes_cliente'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-created_at']

    def __str__(self):
        return self.nome_razao_social


class HistoricoCliente(BaseModel):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='historico')
    descricao = models.TextField('descrição')

    class Meta:
        db_table = 'clientes_historico'
        ordering = ['-created_at']
        verbose_name = 'Histórico'
        verbose_name_plural = 'Históricos'

    def __str__(self):
        return f'{self.cliente} — {self.created_at:%d/%m/%Y}'


class AcionistaCliente(BaseModel):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='acionistas')
    nome = models.CharField('nome', max_length=150)
    email = models.EmailField('e-mail', blank=True)
    cpf = models.CharField('CPF', max_length=11, blank=True, default='')
    telefone = models.CharField('telefone', max_length=20, blank=True)
    whatsapp = models.CharField('whatsapp', max_length=20, blank=True)
    principal = models.BooleanField('principal', default=False)

    class Meta:
        db_table = 'clientes_acionista'
        ordering = ['-principal', 'nome']
        verbose_name = 'Acionista'
        verbose_name_plural = 'Acionistas'

    def save(self, *args, **kwargs):
        if self.principal:
            with transaction.atomic():
                AcionistaCliente.objects.filter(
                    cliente=self.cliente, principal=True
                ).exclude(pk=self.pk).update(principal=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nome} ({self.cliente})'
