from django.conf import settings
from django.db import models

from common.models import BaseModel


class NomeMetodoPagamento(models.TextChoices):
    PIX            = 'PIX',            'PIX'
    BOLETO         = 'BOLETO',         'Boleto'
    CARTAO_CREDITO = 'CARTAO_CREDITO', 'Cartao de Credito'
    CARTAO_DEBITO  = 'CARTAO_DEBITO',  'Cartao de Debito'
    DINHEIRO       = 'DINHEIRO',       'Dinheiro'
    OUTRO          = 'OUTRO',          'Outro'


class MetodoPagamento(BaseModel):
    nome = models.CharField(
        max_length=20, choices=NomeMetodoPagamento.choices,
        unique=True, null=True, blank=True,
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'pag_metodo_pagamento'
        ordering = ['nome']

    def __str__(self):
        return self.get_nome_display()


class StatusCobranca(models.TextChoices):
    PENDENTE  = 'PENDENTE',  'Pendente'
    PAGO      = 'PAGO',      'Pago'
    CANCELADO = 'CANCELADO', 'Cancelado'
    ATRASADO  = 'ATRASADO',  'Atrasado'


class Cobranca(BaseModel):
    cliente        = models.ForeignKey(
        'clientes.Cliente', null=True, blank=True,
        on_delete=models.PROTECT, related_name='cobrancas',
    )
    descricao      = models.CharField(max_length=255, blank=True)
    valor          = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vencimento     = models.DateField(null=True, blank=True)
    status         = models.CharField(
        max_length=10, choices=StatusCobranca.choices, default='PENDENTE',
    )
    metodo         = models.ForeignKey(
        MetodoPagamento, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='cobrancas',
    )
    data_pagamento = models.DateField(null=True, blank=True)
    comprovante    = models.FileField(upload_to='comprovantes/', blank=True)
    observacoes    = models.TextField(blank=True)
    criado_por     = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'pag_cobranca'
        ordering = ['vencimento']

    def __str__(self):
        return f'{self.descricao} — R$ {self.valor}'


class StatusParcela(models.TextChoices):
    PENDENTE  = 'PENDENTE',  'Pendente'
    PAGO      = 'PAGO',      'Pago'
    CANCELADO = 'CANCELADO', 'Cancelado'


class Parcela(BaseModel):
    cobranca       = models.ForeignKey(
        Cobranca, null=True, blank=True, on_delete=models.CASCADE, related_name='parcelas',
    )
    numero         = models.IntegerField(default=1)
    valor          = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vencimento     = models.DateField(null=True, blank=True)
    status         = models.CharField(
        max_length=10, choices=StatusParcela.choices, default='PENDENTE',
    )
    data_pagamento = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'pag_parcela'
        ordering = ['numero']

    def __str__(self):
        return f'Parcela {self.numero} — R$ {self.valor}'
