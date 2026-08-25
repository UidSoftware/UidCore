from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import BaseModel


class UnidadeBase(models.TextChoices):
    UN = 'UN', 'Unidade'
    PT = 'PT', 'Pacote'
    CX = 'CX', 'Caixa'
    KG = 'KG', 'Quilograma'
    L  = 'L',  'Litro'
    M  = 'M',  'Metro'


class Produto(BaseModel):
    nome = models.CharField('nome', max_length=200)
    codigo_barras = models.CharField('código de barras', max_length=50, blank=True, default='')
    quantidade_estoque = models.DecimalField(
        'quantidade em estoque', max_digits=12, decimal_places=3, default=0,
    )
    estoque_minimo = models.DecimalField(
        'estoque mínimo', max_digits=12, decimal_places=3, default=0,
    )
    unidade_base = models.CharField(
        'unidade base', max_length=2,
        choices=UnidadeBase.choices, default=UnidadeBase.UN,
    )
    valor_unitario = models.DecimalField(
        'valor unitário (custo)', max_digits=12, decimal_places=2, default=0,
    )
    preco_venda = models.DecimalField(
        'preço de venda', max_digits=12, decimal_places=2, default=0,
    )
    observacoes = models.TextField('observações', blank=True, default='')

    class Meta:
        db_table = 'prd_produto'
        ordering = ['nome']
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'

    def __str__(self):
        return self.nome


class ConversaoUnidade(BaseModel):
    produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE, related_name='conversoes',
    )
    unidade = models.CharField('unidade', max_length=2, choices=UnidadeBase.choices)
    converte_para = models.CharField(
        'converte para', max_length=2, choices=UnidadeBase.choices,
        null=True, blank=True,
        help_text=(
            'Unidade de referência desta conversão (deve já existir como '
            'unidade_base do produto ou como outra ConversaoUnidade dele). '
            'Vazio = relativo à unidade_base do produto (comportamento '
            'legado, retrocompatível — Manutenção #37).'
        ),
    )
    quantidade_por_base = models.DecimalField(
        'quantidade por unidade base', max_digits=12, decimal_places=3,
        help_text=(
            'Quantos de `converte_para` (ou da unidade_base, se '
            '`converte_para` vazio) equivalem a 1 desta `unidade`. '
            'Ex: 1 CX = 30 UN → quantidade_por_base=30'
        ),
    )

    class Meta:
        db_table = 'prd_conversao_unidade'
        unique_together = [('produto', 'unidade')]
        verbose_name = 'Conversão de Unidade'
        verbose_name_plural = 'Conversões de Unidade'

    def __str__(self):
        return f'{self.produto.nome}: 1 {self.unidade} = {self.quantidade_por_base} {self.produto.unidade_base}'


class EntradaEstoque(BaseModel):
    produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE, related_name='entradas',
    )
    quantidade = models.DecimalField('quantidade', max_digits=12, decimal_places=3)
    unidade = models.CharField('unidade', max_length=2, choices=UnidadeBase.choices)
    quantidade_base = models.DecimalField(
        'quantidade em unidade base', max_digits=12, decimal_places=3, default=0,
        help_text='Calculado automaticamente no save()',
    )
    nota_fiscal = models.CharField('nota fiscal', max_length=50, blank=True, default='')
    observacoes = models.TextField('observações', blank=True, default='')
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'prd_entrada_estoque'
        ordering = ['-created_at']
        verbose_name = 'Entrada de Estoque'
        verbose_name_plural = 'Entradas de Estoque'

    def save(self, *args, **kwargs):
        # Converter quantidade para unidade base — resolve cadeia (RN-01)
        # via produtos.services.fator_para_base; RN-05: sem fallback 1:1
        # silencioso — unidade sem conversão cadastrada levanta ValidationError.
        from .services import fator_para_base

        if self.unidade == self.produto.unidade_base:
            self.quantidade_base = self.quantidade
        else:
            fator = fator_para_base(self.produto, self.unidade)
            self.quantidade_base = self.quantidade * fator

        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Atualizar estoque do produto somente em criações (não em updates)
        if is_new:
            Produto.objects.filter(pk=self.produto_id).update(
                quantidade_estoque=models.F('quantidade_estoque') + self.quantidade_base,
            )

    def __str__(self):
        return f'Entrada {self.quantidade} {self.unidade} — {self.produto.nome}'


class Combo(BaseModel):
    nome = models.CharField('nome', max_length=200)
    descricao = models.TextField('descrição', blank=True, default='')
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='combos_criados',
    )

    class Meta:
        db_table = 'prd_combo'
        ordering = ['-created_at']
        verbose_name = 'Combo'
        verbose_name_plural = 'Combos'

    @property
    def valor_total(self):
        return sum((item.subtotal for item in self.itens.all()), Decimal('0.00'))

    def __str__(self):
        return self.nome


class ItemCombo(models.Model):
    # Sem BaseModel proposital: item filho de Combo, ciclo de vida
    # atrelado 1:1 ao pai (delete-and-recreate no update — RN-04);
    # não precisa de is_active/soft delete próprio, mesma decisão da
    # origem (SystemD ItemCombo também não herda soft delete próprio).
    combo = models.ForeignKey(Combo, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='combo_itens')
    quantidade = models.DecimalField('quantidade', max_digits=12, decimal_places=3, default=1)
    valor_unitario = models.DecimalField(
        'valor unitário', max_digits=12, decimal_places=2, default=Decimal('0.00'),
        help_text='Snapshot no momento de salvar — não referencia Produto '
                   'dinamicamente (RN-03).',
    )

    class Meta:
        db_table = 'prd_item_combo'
        verbose_name = 'Item do Combo'
        verbose_name_plural = 'Itens do Combo'

    @property
    def subtotal(self):
        return self.quantidade * self.valor_unitario

    def __str__(self):
        return f'{self.combo.nome} — {self.produto.nome} x{self.quantidade}'
