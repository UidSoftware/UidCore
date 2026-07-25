from decimal import Decimal

from django.db import models

from common.models import BaseModel


class Cargo(BaseModel):
    nome         = models.CharField(max_length=100, unique=True)
    descricao    = models.TextField(blank=True)
    salario_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'rh_cargo'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class RegimeTrabalhista(models.TextChoices):
    CLT     = 'CLT',     'CLT'
    PJ      = 'PJ',      'PJ'
    ESTAGIO = 'ESTAGIO', 'Estagio'
    SOCIO   = 'SOCIO',   'Socio'


class Funcionario(BaseModel):
    nome           = models.CharField(max_length=255)
    cpf            = models.CharField(max_length=11, unique=True)
    email          = models.EmailField(blank=True)
    cargo          = models.ForeignKey(Cargo, on_delete=models.PROTECT, related_name='funcionarios')
    data_admissao  = models.DateField()
    data_demissao  = models.DateField(null=True, blank=True)
    salario_atual  = models.DecimalField(max_digits=12, decimal_places=2)
    regime         = models.CharField(
        max_length=8, choices=RegimeTrabalhista.choices, default='CLT',
    )
    observacoes    = models.TextField(blank=True)

    class Meta:
        db_table = 'rh_funcionario'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class StatusFolha(models.TextChoices):
    ABERTA  = 'ABERTA',  'Aberta'
    FECHADA = 'FECHADA', 'Fechada'
    PAGA    = 'PAGA',    'Paga'


class FolhaPagamento(BaseModel):
    funcionario    = models.ForeignKey(Funcionario, on_delete=models.PROTECT, related_name='folhas')
    mes_referencia = models.DateField()
    salario_bruto  = models.DecimalField(max_digits=12, decimal_places=2)
    descontos      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    salario_liquido = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    status         = models.CharField(
        max_length=8, choices=StatusFolha.choices, default='ABERTA',
    )
    observacoes    = models.TextField(blank=True)

    class Meta:
        db_table = 'rh_folha_pagamento'
        ordering = ['-mes_referencia']

    def save(self, *args, **kwargs):
        self.salario_liquido = self.salario_bruto - (self.descontos or Decimal('0'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.funcionario} — {self.mes_referencia.strftime("%m/%Y")}'


class StatusFerias(models.TextChoices):
    AGENDADO    = 'AGENDADO',    'Agendado'
    EM_ANDAMENTO = 'EM_ANDAMENTO', 'Em Andamento'
    CONCLUIDO   = 'CONCLUIDO',   'Concluido'


class RegistroFerias(BaseModel):
    funcionario = models.ForeignKey(Funcionario, on_delete=models.PROTECT, related_name='ferias')
    data_inicio = models.DateField()
    data_fim    = models.DateField()
    dias        = models.IntegerField(editable=False, default=0)
    status      = models.CharField(
        max_length=12, choices=StatusFerias.choices, default='AGENDADO',
    )

    class Meta:
        db_table = 'rh_registro_ferias'
        ordering = ['-data_inicio']

    def save(self, *args, **kwargs):
        self.dias = (self.data_fim - self.data_inicio).days
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.funcionario} — {self.data_inicio} a {self.data_fim}'
