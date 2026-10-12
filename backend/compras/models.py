"""
compras/models.py — Manutencao #58 (Fase 2).

Amarra as 3 pontas que hoje ficam desconectadas no fluxo de "comprei
mercadoria": fornecedor -> itens comprados com custo -> lancamento
financeiro (Despesa) -> entrada de estoque (MovimentoEstoque).

Reaproveita 100% do mecanismo ja em producao:
- MovimentoEstoque.save() (Fase 1, produtos/models.py) resolve conversao
  de unidade via produtos.services.fator_para_base e atualiza
  Produto.quantidade_estoque via F() atomico — NAO duplicado aqui.
- financeiro.signals.despesa_para_livro_caixa cria o LivroCaixa sozinho
  quando Despesa.status == 'PAGO' — compras NUNCA escreve em LivroCaixa
  diretamente (ver compras/signals.py).
"""
from decimal import Decimal

from django.db import models

from common.models import BaseModel
from fornecedores.models import Fornecedor
from financeiro.models import Conta, Despesa, FormaPagamento
from produtos.models import MovimentoEstoque, Produto, TipoMovimento, UnidadeBase


class StatusCompra(models.TextChoices):
    PENDENTE = 'PENDENTE', 'Pendente'
    PAGO = 'PAGO', 'Pago'
    CANCELADO = 'CANCELADO', 'Cancelado'


class Compra(BaseModel):
    fornecedor = models.ForeignKey(
        Fornecedor, on_delete=models.PROTECT, related_name='compras',
    )
    conta = models.ForeignKey(
        Conta, on_delete=models.PROTECT, related_name='compras',
    )
    numero_nota_fiscal = models.CharField(
        'número da nota fiscal', max_length=50, blank=True, default='',
    )
    data_emissao = models.DateField('data de emissão')
    forma_pagamento = models.CharField(
        'forma de pagamento', max_length=20,
        choices=FormaPagamento.choices, blank=True, default='',
    )
    status = models.CharField(
        'status', max_length=20,
        choices=StatusCompra.choices, default=StatusCompra.PENDENTE,
    )
    valor_total = models.DecimalField(
        'valor total', max_digits=12, decimal_places=2,
        default=0, editable=False,
        help_text='Calculado no create() do serializer a partir da soma '
                   'dos itens — nunca editável via payload direto (RF-06).',
    )
    observacoes = models.TextField('observações', blank=True, default='')
    # OneToOne (nao FK) porque uma Compra gera exatamente 1 Despesa nesta
    # fase (RF-02/decisao de arquitetura). SET_NULL porque Despesa e
    # soft-delete (is_active=False) — a referencia nao pode travar uma
    # futura exclusao logica da Despesa fora deste fluxo. related_name
    # 'compra' expoe despesa.compra sem precisar tocar em financeiro/models.py.
    despesa = models.OneToOneField(
        Despesa, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='compra',
    )

    class Meta:
        db_table = 'cmp_compra'
        ordering = ['-data_emissao', '-created_at']
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'

    def __str__(self):
        return f'Compra #{self.pk} — {self.fornecedor.nome_razao_social} — R$ {self.valor_total}'


class ItemCompra(BaseModel):
    # Herda BaseModel (Manutencao 62 — auditoria) apenas por consistencia
    # de schema: item filho de Compra, ciclo de vida atrelado ao pai,
    # imutavel apos criacao (RN-05) — mesmo racional de ItemCombo
    # (Manutencao 53). Sem ViewSet/acao propria — created_by/updated_by
    # ficam null (nao preenchidos automaticamente, fora de escopo).
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='compra_itens')
    quantidade = models.DecimalField('quantidade', max_digits=12, decimal_places=3)
    unidade = models.CharField('unidade', max_length=2, choices=UnidadeBase.choices)
    valor_unitario_custo = models.DecimalField(
        'valor unitário de custo', max_digits=12, decimal_places=2,
    )
    # Populado no save() ao criar o MovimentoEstoque de ENTRADA (RF-04).
    movimento_estoque = models.OneToOneField(
        MovimentoEstoque, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='item_compra',
    )

    class Meta:
        db_table = 'cmp_item_compra'
        verbose_name = 'Item da Compra'
        verbose_name_plural = 'Itens da Compra'

    @property
    def subtotal(self):
        return self.quantidade * self.valor_unitario_custo

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # RF-04: reaproveita 100% o MovimentoEstoque.save() da Fase 1
            # (conversao de unidade via fator_para_base + F() atomico em
            # Produto.quantidade_estoque). Nenhuma logica de estoque e
            # duplicada aqui. Se a unidade nao tiver conversao cadastrada,
            # MovimentoEstoque.save() levanta django.core.exceptions.
            # ValidationError, que borbulha ate o serializer/view — a
            # validacao real ja aconteceu antes em ItemCompraSerializer.
            # validate() (RN-01), entao aqui e so a segunda linha de defesa.
            movimento = MovimentoEstoque.objects.create(
                produto=self.produto,
                tipo=TipoMovimento.ENTRADA,
                quantidade=self.quantidade,
                unidade=self.unidade,
                nota_fiscal=self.compra.numero_nota_fiscal,
                observacoes=(
                    f'Compra #{self.compra_id} — '
                    f'{self.compra.fornecedor.nome_razao_social}'
                ),
            )
            ItemCompra.objects.filter(pk=self.pk).update(movimento_estoque=movimento)
            self.movimento_estoque = movimento
            # RF-05: ultimo custo sobrescreve Produto.valor_unitario — regra
            # mais simples adotada nesta fase (documentado na Especificacao
            # Hotfix, secao 2). update() atomico, mesmo padrao do F() ja
            # usado em MovimentoEstoque.save() (sem race condition com
            # outra escrita concorrente de estoque).
            Produto.objects.filter(pk=self.produto_id).update(
                valor_unitario=self.valor_unitario_custo,
            )

    def __str__(self):
        return f'{self.compra} — {self.produto.nome} x{self.quantidade}'
