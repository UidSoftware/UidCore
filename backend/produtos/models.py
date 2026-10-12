from decimal import Decimal

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


class TipoMovimento(models.TextChoices):
    ENTRADA = 'ENTRADA', 'Entrada'
    ENTRADA_INICIAL = 'ENTRADA_INICIAL', 'Estoque Inicial'
    DEVOLUCAO_CLIENTE = 'DEVOLUCAO_CLIENTE', 'Devolução de Cliente'
    PERDA = 'PERDA', 'Perda/Quebra'
    AJUSTE = 'AJUSTE', 'Ajuste de Inventário'
    SAIDA_MANUAL = 'SAIDA_MANUAL', 'Saída Manual'


# Tipos cujo efeito sobre Produto.quantidade_estoque é sempre negativo.
# AJUSTE tem sinal embutido na própria `quantidade` (pode ser negativa) —
# não entra aqui. Os demais tipos (ENTRADA/ENTRADA_INICIAL/DEVOLUCAO_CLIENTE)
# são sempre positivos, validados no serializer (RN-01, Manutencao 58).
EFEITO_NEGATIVO = {TipoMovimento.PERDA, TipoMovimento.SAIDA_MANUAL}


class MovimentoEstoque(BaseModel):
    """
    Generalização de EntradaEstoque (Manutencao 58 — antes só suportava
    entradas, sempre positivas). Herda o padrão atômico de save() com
    F() expression e a resolução de cadeia de unidade via
    produtos.services.fator_para_base (Manutencao 37) — RN-05: sem
    fallback 1:1 silencioso, unidade sem conversão cadastrada levanta
    ValidationError. Único consumidor do endpoint é frontend/Produtos.jsx
    (confirmado na Especificacao_Hotfix.md da Manutencao 58) — o módulo
    pdv NÃO usa este model, só a função fator_para_base.
    """
    produto = models.ForeignKey(
        Produto, on_delete=models.CASCADE, related_name='movimentos',
    )
    tipo = models.CharField(
        'tipo', max_length=20, choices=TipoMovimento.choices,
        default=TipoMovimento.ENTRADA,
    )
    quantidade = models.DecimalField(
        'quantidade', max_digits=12, decimal_places=3,
        help_text='Pode ser negativa somente quando tipo=AJUSTE.',
    )
    unidade = models.CharField('unidade', max_length=2, choices=UnidadeBase.choices)
    quantidade_base = models.DecimalField(
        'quantidade em unidade base', max_digits=12, decimal_places=3, default=0,
        help_text='Calculado automaticamente no save()',
    )
    nota_fiscal = models.CharField('nota fiscal', max_length=50, blank=True, default='')
    observacoes = models.TextField(
        'observações', blank=True, default='',
        help_text='Funciona como "motivo" do movimento — obrigatório '
                   'para todo tipo exceto ENTRADA/ENTRADA_INICIAL (RN-02).',
    )

    class Meta:
        db_table = 'prd_movimento_estoque'
        ordering = ['-created_at']
        verbose_name = 'Movimento de Estoque'
        verbose_name_plural = 'Movimentos de Estoque'

    def save(self, *args, **kwargs):
        # Converter quantidade para unidade base — resolve cadeia (RN-01)
        # via produtos.services.fator_para_base; RN-05: sem fallback 1:1
        # silencioso — unidade sem conversão cadastrada levanta ValidationError.
        from .services import fator_para_base

        if self.unidade == self.produto.unidade_base:
            fator = Decimal('1')
        else:
            fator = fator_para_base(self.produto, self.unidade)
        self.quantidade_base = self.quantidade * fator

        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Atualizar estoque do produto somente em criações (não em updates
        # — RN-06: editar um movimento passado não deve re-somar o efeito).
        if is_new:
            delta = (
                -self.quantidade_base if self.tipo in EFEITO_NEGATIVO
                else self.quantidade_base
            )
            Produto.objects.filter(pk=self.produto_id).update(
                quantidade_estoque=models.F('quantidade_estoque') + delta,
            )

    def __str__(self):
        return f'{self.get_tipo_display()} {self.quantidade} {self.unidade} — {self.produto.nome}'


class Combo(BaseModel):
    nome = models.CharField('nome', max_length=200)
    descricao = models.TextField('descrição', blank=True, default='')

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


class ItemCombo(BaseModel):
    # Herda BaseModel (Manutencao 62 — auditoria) apenas por consistencia
    # de schema: item filho de Combo, ciclo de vida atrelado 1:1 ao pai
    # (delete-and-recreate no update — RN-04). Sem ViewSet/acao propria —
    # created_by/updated_by ficam null (nao preenchidos automaticamente,
    # fora de escopo desta manutencao).
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
