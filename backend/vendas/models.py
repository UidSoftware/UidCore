from datetime import date

from django.conf import settings
from django.db import models

from common.models import BaseModel


class StatusOrcamento(models.TextChoices):
    RASCUNHO  = 'RASCUNHO',  'Rascunho'
    ENVIADO   = 'ENVIADO',   'Enviado'
    APROVADO  = 'APROVADO',  'Aprovado'
    REJEITADO = 'REJEITADO', 'Rejeitado'
    CANCELADO = 'CANCELADO', 'Cancelado'


class Orcamento(BaseModel):
    numero      = models.CharField(max_length=20, unique=True, blank=True)
    cliente     = models.ForeignKey(
        'clientes.Cliente', null=True, blank=True,
        on_delete=models.PROTECT, related_name='orcamentos',
    )
    descricao   = models.TextField(blank=True)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status      = models.CharField(
        max_length=10, choices=StatusOrcamento.choices, default='RASCUNHO',
    )
    validade    = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    criado_por  = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'vnd_orcamento'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.numero:
            ano = date.today().year
            ultimo = (
                Orcamento.objects.filter(numero__startswith=f'ORC-{ano}-')
                .order_by('-numero')
                .first()
            )
            if ultimo:
                try:
                    seq = int(ultimo.numero.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1
            self.numero = f'ORC-{ano}-{seq:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.numero} — {self.cliente}'


class StatusPedido(models.TextChoices):
    PENDENTE     = 'PENDENTE',     'Pendente'
    CONFIRMADO   = 'CONFIRMADO',   'Confirmado'
    EM_PRODUCAO  = 'EM_PRODUCAO',  'Em Producao'
    ENTREGUE     = 'ENTREGUE',     'Entregue'
    CANCELADO    = 'CANCELADO',    'Cancelado'


class Pedido(BaseModel):
    numero               = models.CharField(max_length=20, unique=True, blank=True)
    cliente              = models.ForeignKey(
        'clientes.Cliente', null=True, blank=True,
        on_delete=models.PROTECT, related_name='pedidos',
    )
    orcamento            = models.ForeignKey(
        Orcamento, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='pedidos',
    )
    status               = models.CharField(
        max_length=12, choices=StatusPedido.choices, default='PENDENTE',
    )
    valor_total          = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    data_pedido          = models.DateField(default=date.today)
    data_entrega_prevista = models.DateField(null=True, blank=True)
    observacoes          = models.TextField(blank=True)
    criado_por           = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'vnd_pedido'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.numero:
            ano = date.today().year
            ultimo = (
                Pedido.objects.filter(numero__startswith=f'PED-{ano}-')
                .order_by('-numero')
                .first()
            )
            if ultimo:
                try:
                    seq = int(ultimo.numero.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1
            self.numero = f'PED-{ano}-{seq:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.numero} — {self.cliente}'


class ItemOrcamento(BaseModel):
    orcamento      = models.ForeignKey(
        Orcamento, on_delete=models.CASCADE, related_name='itens',
    )
    produto        = models.ForeignKey(
        'produtos.Produto', null=True, blank=True,
        on_delete=models.PROTECT, related_name='itens_orcamento',
    )
    descricao      = models.CharField(max_length=500, blank=True)
    quantidade     = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_total    = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)

    class Meta:
        db_table = 'vnd_item_orcamento'
        ordering = ['id']

    def save(self, *args, **kwargs):
        self.valor_total = self.quantidade * self.valor_unitario
        if self.produto and not self.descricao:
            self.descricao = self.produto.nome
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.descricao} x{self.quantidade}'


class ItemPedido(BaseModel):
    pedido         = models.ForeignKey(
        Pedido, null=True, blank=True, on_delete=models.CASCADE, related_name='itens',
    )
    produto        = models.ForeignKey(
        'produtos.Produto', null=True, blank=True,
        on_delete=models.PROTECT, related_name='itens_pedido',
    )
    descricao      = models.CharField(max_length=255, blank=True)
    quantidade     = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_total    = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)

    class Meta:
        db_table = 'vnd_item_pedido'
        ordering = ['id']

    def save(self, *args, **kwargs):
        self.valor_total = self.quantidade * self.valor_unitario
        if self.produto and not self.descricao:
            self.descricao = self.produto.nome
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.descricao} x{self.quantidade}'
