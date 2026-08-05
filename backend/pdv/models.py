"""
Models do módulo PDV (Ponto de Venda).

App separado de `vendas` por decisão de arquitetura (ADR-015):
  - vendas.Pedido = fluxo de encomenda B2B (sem baixa de estoque, sem Receita/LivroCaixa)
  - pdv.Venda     = venda de balcão à vista (baixa de estoque síncrona, split de pagamento,
                    geração automática de Receita/LivroCaixa)
"""
from decimal import Decimal
from datetime import date

from django.conf import settings
from django.db import models

from common.models import BaseModel
from produtos.models import UnidadeBase


# ---------------------------------------------------------------------------
# SessaoCaixa
# ---------------------------------------------------------------------------

class StatusSessaoCaixa(models.TextChoices):
    ABERTA  = 'ABERTA',  'Aberta'
    FECHADA = 'FECHADA', 'Fechada'


class SessaoCaixa(BaseModel):
    """
    Sessão de caixa físico.

    RN-01: no máximo 1 sessão ABERTA por conta (não global).
    A UniqueConstraint condicional é a barreira de última linha; a validação
    primária está em services.abrir_sessao() com select_for_update() dentro
    de transaction.atomic(), para retornar 400 legível em vez de 500
    IntegrityError.
    """
    conta = models.ForeignKey(
        'financeiro.Conta',
        on_delete=models.PROTECT,
        related_name='sessoes_caixa',
    )
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sessoes_caixa',
    )
    valor_abertura = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    data_abertura = models.DateTimeField(auto_now_add=True)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    valor_fechamento_informado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    valor_fechamento_calculado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    diferenca = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    status = models.CharField(
        max_length=10,
        choices=StatusSessaoCaixa.choices,
        default=StatusSessaoCaixa.ABERTA,
    )
    observacoes = models.TextField(blank=True)

    class Meta:
        db_table = 'pdv_sessao_caixa'
        ordering = ['-data_abertura']
        constraints = [
            models.UniqueConstraint(
                fields=['conta'],
                condition=models.Q(status='ABERTA'),
                name='uniq_sessao_aberta_por_conta',
            ),
        ]

    def __str__(self):
        return f'Sessao #{self.pk} — {self.conta.nome} ({self.status})'


# ---------------------------------------------------------------------------
# MovimentoCaixa
# ---------------------------------------------------------------------------

class TipoMovimentoCaixa(models.TextChoices):
    SANGRIA    = 'SANGRIA',    'Sangria'
    SUPRIMENTO = 'SUPRIMENTO', 'Suprimento'


class MovimentoCaixa(BaseModel):
    """
    Sangria/suprimento de gaveta.

    NÃO gera Receita/Despesa/LivroCaixa diretamente (é movimentação física,
    entra apenas no cálculo de valor_fechamento_calculado da sessão).
    """
    sessao = models.ForeignKey(
        SessaoCaixa,
        on_delete=models.PROTECT,
        related_name='movimentos',
    )
    tipo = models.CharField(max_length=10, choices=TipoMovimentoCaixa.choices)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    motivo = models.TextField()
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='+',
    )
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pdv_movimento_caixa'
        ordering = ['-data_hora']

    def __str__(self):
        return f'{self.tipo} R$ {self.valor} — sessao #{self.sessao_id}'


# ---------------------------------------------------------------------------
# Venda
# ---------------------------------------------------------------------------

class StatusVenda(models.TextChoices):
    ABERTA     = 'ABERTA',     'Aberta'
    FINALIZADA = 'FINALIZADA', 'Finalizada'
    CANCELADA  = 'CANCELADA',  'Cancelada'


class Venda(BaseModel):
    """
    Venda de balcão a vista (PDV).

    Numeração automática: VDA-YYYY-NNNN (mesmo padrão de Orcamento/Pedido em vendas/).
    FK receita não existe aqui — uma venda pode gerar N Receitas (uma por
    PagamentoVenda no split). A relação se lê via PagamentoVenda.receita.
    """
    numero = models.CharField(max_length=20, unique=True, blank=True)  # VDA-YYYY-NNNN
    sessao_caixa = models.ForeignKey(
        SessaoCaixa,
        on_delete=models.PROTECT,
        related_name='vendas',
    )
    cliente = models.ForeignKey(
        'clientes.Cliente',
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='vendas_pdv',
    )
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='vendas_pdv',
    )
    status = models.CharField(
        max_length=12,
        choices=StatusVenda.choices,
        default=StatusVenda.ABERTA,
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    desconto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_total = models.DecimalField(
        max_digits=12, decimal_places=2, editable=False, default=0,
    )
    data_hora = models.DateTimeField(auto_now_add=True)
    cancelada_em = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.TextField(blank=True)

    class Meta:
        db_table = 'pdv_venda'
        ordering = ['-data_hora']

    def save(self, *args, **kwargs):
        if not self.numero:
            ano = date.today().year
            ultimo = (
                Venda.objects.filter(numero__startswith=f'VDA-{ano}-')
                .order_by('-numero')
                .first()
            )
            seq = 1
            if ultimo:
                try:
                    seq = int(ultimo.numero.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            self.numero = f'VDA-{ano}-{seq:04d}'
        super().save(*args, **kwargs)

    def recalcular_total(self):
        """Recalcula subtotal e valor_total a partir dos itens ativos."""
        from django.db.models import Sum as _Sum
        agregado = self.itens.filter(is_active=True).aggregate(v=_Sum('valor_total'))
        self.subtotal = agregado['v'] or Decimal('0')
        self.valor_total = self.subtotal - self.desconto_total
        self.save(update_fields=['subtotal', 'valor_total'])

    def __str__(self):
        return f'{self.numero} — {self.status}'


# ---------------------------------------------------------------------------
# ItemVenda
# ---------------------------------------------------------------------------

class ItemVenda(BaseModel):
    """
    Item do carrinho de uma Venda.

    RN-03: valor_unitario é snapshot de Produto.preco_venda no momento da
    venda — nunca aceito do payload, nunca recalculado se o preço mudar.
    quantidade_estornada rastreia devoluções parciais (Ponto 2 / RF-13).
    """
    venda = models.ForeignKey(
        Venda,
        on_delete=models.CASCADE,
        related_name='itens',
    )
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='itens_venda_pdv',
    )
    quantidade = models.DecimalField(max_digits=12, decimal_places=3)
    unidade = models.CharField(max_length=2, choices=UnidadeBase.choices)
    valor_unitario = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text='Snapshot de Produto.preco_venda no momento da venda (RN-03).',
    )
    desconto_item = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_total = models.DecimalField(
        max_digits=12, decimal_places=2, editable=False, default=0,
    )
    quantidade_estornada = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        help_text='Quantidade devolvida parcialmente (RF-13).',
    )

    class Meta:
        db_table = 'pdv_item_venda'
        ordering = ['id']

    def save(self, *args, **kwargs):
        self.valor_total = (
            (self.quantidade * self.valor_unitario) - self.desconto_item
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.produto.nome} x{self.quantidade}'


# ---------------------------------------------------------------------------
# PagamentoVenda
# ---------------------------------------------------------------------------

class PagamentoVenda(BaseModel):
    """
    Uma parcela do split de pagamento de uma Venda.

    conta = conta de destino resolvida em services.finalizar_venda():
      1. payload['conta'] se presente
      2. MetodoPagamento.conta_padrao se configurado (ADR-018)
      3. erro 400 se nenhum dos dois (RF-14)

    receita é nullable até a Receita ser criada na finalização (RF-08).
    Para metodo.nome == CARTAO_CREDITO existe também a relação 1:1
    RecebivelCartao (FK inversa recebivel_cartao).
    """
    venda = models.ForeignKey(
        Venda,
        on_delete=models.CASCADE,
        related_name='pagamentos',
    )
    metodo = models.ForeignKey(
        'pagamentos.MetodoPagamento',
        on_delete=models.PROTECT,
        related_name='pagamentos_venda',
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    conta = models.ForeignKey(
        'financeiro.Conta',
        on_delete=models.PROTECT,
        related_name='pagamentos_venda',
    )
    receita = models.ForeignKey(
        'financeiro.Receita',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='pagamento_venda_origem',
    )

    class Meta:
        db_table = 'pdv_pagamento_venda'
        ordering = ['id']

    def __str__(self):
        return f'{self.metodo} R$ {self.valor} — venda {self.venda_id}'


# ---------------------------------------------------------------------------
# RecebivelCartao
# ---------------------------------------------------------------------------

class StatusRecebivelCartao(models.TextChoices):
    PREVISTO  = 'PREVISTO',  'Previsto'
    LIQUIDADO = 'LIQUIDADO', 'Liquidado'
    CANCELADO = 'CANCELADO', 'Cancelado'


class RecebivelCartao(BaseModel):
    """
    Recebível de cartão de crédito com taxa e prazo de liquidação (Ponto 3).

    Nasce PREVISTO junto com uma Receita status=PENDENTE na finalização da
    venda. Nenhum LivroCaixa nasce ainda — o signal receita_para_livro_caixa
    só dispara com status=RECEBIDO. A liquidação acontece exclusivamente via
    ConciliacaoViewSet.confirmar_item (ADR-019).

    RN-06: nunca vira LIQUIDADO automaticamente por data — sempre exige
    confirmação humana via conciliação bancária.
    """
    pagamento = models.OneToOneField(
        PagamentoVenda,
        on_delete=models.PROTECT,
        related_name='recebivel_cartao',
    )
    receita = models.OneToOneField(
        'financeiro.Receita',
        on_delete=models.PROTECT,
        related_name='recebivel_cartao',
    )
    taxa_percentual = models.DecimalField(max_digits=5, decimal_places=2)
    valor_bruto = models.DecimalField(max_digits=12, decimal_places=2)
    valor_liquido_previsto = models.DecimalField(
        max_digits=12, decimal_places=2, editable=False,
    )
    data_prevista_liquidacao = models.DateField()
    data_liquidacao = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=StatusRecebivelCartao.choices,
        default=StatusRecebivelCartao.PREVISTO,
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    class Meta:
        db_table = 'pdv_recebivel_cartao'
        ordering = ['data_prevista_liquidacao']

    def __str__(self):
        return f'Recebivel cartao R$ {self.valor_liquido_previsto} — {self.status}'
