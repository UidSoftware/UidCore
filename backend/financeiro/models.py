from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import BaseModel


class TipoConta(models.TextChoices):
    CORRENTE = 'CORRENTE', 'Conta Corrente'
    POUPANCA = 'POUPANCA', 'Poupança'
    CAIXA = 'CAIXA', 'Caixa'
    CARTEIRA = 'CARTEIRA', 'Carteira Digital'


class Conta(BaseModel):
    nome = models.CharField(max_length=100, blank=True)
    tipo = models.CharField(max_length=20, choices=TipoConta.choices, blank=True)
    banco = models.CharField(max_length=100, blank=True)
    agencia = models.CharField(max_length=20, blank=True)
    numero = models.CharField(max_length=30, blank=True)
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'fin_conta'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class TipoAporte(models.TextChoices):
    CAPITAL_SOCIAL = 'CAPITAL_SOCIAL', 'Capital Social'
    SOCIO = 'SOCIO', 'Aporte do Fundador'
    INVESTIDOR = 'INVESTIDOR', 'Aporte de Investidor'
    EMPRESTIMO = 'EMPRESTIMO', 'Empréstimo'


class Aporte(BaseModel):
    tipo = models.CharField(max_length=20, choices=TipoAporte.choices, blank=True)
    descricao = models.CharField(max_length=255, blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='aportes')
    data = models.DateField(null=True, blank=True)
    responsavel = models.CharField(max_length=150, blank=True)
    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'fin_aporte'
        ordering = ['-data']

    def __str__(self):
        return f'{self.descricao} — R$ {self.valor}'


class TipoCategoria(models.TextChoices):
    ENTRADA = 'ENTRADA', 'Entrada'
    SAIDA = 'SAIDA', 'Saída'


class Categoria(BaseModel):
    nome = models.CharField(max_length=100, blank=True)
    tipo = models.CharField(max_length=10, choices=TipoCategoria.choices, blank=True)

    class Meta:
        ordering = ['nome']
        unique_together = [['nome', 'tipo']]
        db_table = 'fin_categoria'

    def __str__(self):
        return f'{self.nome} ({self.tipo})'


class TipoReceita(models.TextChoices):
    SERVICO = 'SERVICO', 'Serviço'
    PRODUTO = 'PRODUTO', 'Produto'
    MENSALIDADE = 'MENSALIDADE', 'Mensalidade'
    RECEITA_FINANCEIRA = 'RECEITA_FINANCEIRA', 'Receita Financeira'
    OUTRO = 'OUTRO', 'Outro'


class StatusReceita(models.TextChoices):
    PENDENTE = 'PENDENTE', 'Pendente'
    RECEBIDO = 'RECEBIDO', 'Recebido'
    CANCELADO = 'CANCELADO', 'Cancelado'
    ATRASADO = 'ATRASADO', 'Atrasado'


class Receita(BaseModel):
    tipo = models.CharField(max_length=20, choices=TipoReceita.choices, blank=True)
    descricao = models.CharField(max_length=255, blank=True)
    cliente = models.ForeignKey(
        'clientes.Cliente', null=True, blank=True,
        on_delete=models.PROTECT, related_name='receitas',
    )
    categoria = models.ForeignKey(
        'Categoria', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='receitas',
        limit_choices_to={'tipo': 'ENTRADA', 'is_active': True},
    )
    valor_bruto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    desconto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_liquido = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='receitas')
    vencimento = models.DateField(null=True, blank=True)
    recebimento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=StatusReceita.choices, default='PENDENTE')
    referencia_mes = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'fin_receita'
        ordering = ['vencimento']

    def save(self, *args, **kwargs):
        self.valor_liquido = self.valor_bruto - (self.desconto or Decimal('0'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.descricao} — R$ {self.valor_liquido}'


class TipoDespesa(models.TextChoices):
    FIXA = 'FIXA', 'Despesa Fixa'
    VARIAVEL = 'VARIAVEL', 'Despesa Variável'
    PROLABORE = 'PROLABORE', 'Pró-labore'
    IMPOSTO = 'IMPOSTO', 'Imposto / DAS'
    OUTRO = 'OUTRO', 'Outro'


class StatusDespesa(models.TextChoices):
    PENDENTE = 'PENDENTE', 'Pendente'
    PAGO = 'PAGO', 'Pago'
    CANCELADO = 'CANCELADO', 'Cancelado'
    ATRASADO = 'ATRASADO', 'Atrasado'


class FormaPagamento(models.TextChoices):
    PIX = 'PIX', 'PIX'
    TED_DOC = 'TED_DOC', 'TED/DOC'
    BOLETO = 'BOLETO', 'Boleto'
    CARTAO_DEBITO = 'CARTAO_DEBITO', 'Cartão de Débito'
    CARTAO_CREDITO = 'CARTAO_CREDITO', 'Cartão de Crédito'
    DINHEIRO = 'DINHEIRO', 'Dinheiro'
    OUTRO = 'OUTRO', 'Outro'


class Despesa(BaseModel):
    tipo = models.CharField(max_length=20, choices=TipoDespesa.choices, blank=True)
    descricao = models.CharField(max_length=255, blank=True)
    fornecedor = models.CharField(max_length=150, blank=True)
    valor_bruto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    desconto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_liquido = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='despesas')
    categoria = models.ForeignKey(
        'Categoria', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='despesas',
        limit_choices_to={'tipo': 'SAIDA', 'is_active': True},
    )
    vencimento = models.DateField(null=True, blank=True)
    pagamento = models.DateField(null=True, blank=True)
    forma_pagamento = models.CharField(
        max_length=20, choices=FormaPagamento.choices, blank=True,
    )
    status = models.CharField(max_length=20, choices=StatusDespesa.choices, default='PENDENTE')
    referencia_mes = models.DateField(null=True, blank=True)
    comprovante = models.FileField(upload_to='despesas/', blank=True)
    observacoes = models.TextField(blank=True)
    recorrente = models.BooleanField(default=False)
    frequencia = models.CharField(max_length=20, blank=True)
    quantidade = models.PositiveIntegerField(default=1)
    estornado = models.BooleanField(default=False)
    data_estorno = models.DateField(null=True, blank=True)
    motivo_estorno = models.TextField(blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'fin_despesa'
        ordering = ['vencimento']

    def save(self, *args, **kwargs):
        self.valor_liquido = self.valor_bruto - (self.desconto or Decimal('0'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.descricao} — R$ {self.valor_liquido}'


class TipoLancamento(models.TextChoices):
    ENTRADA = 'ENTRADA', 'Entrada'
    SAIDA = 'SAIDA', 'Saída'


class OrigemLancamento(models.TextChoices):
    APORTE = 'APORTE', 'Aporte'
    RECEITA = 'RECEITA', 'Receita'
    DESPESA = 'DESPESA', 'Despesa'
    MANUAL = 'MANUAL', 'Lançamento Manual'
    TRANSFER = 'TRANSFER', 'Transferência'
    ESTORNO = 'ESTORNO', 'Estorno'


class LivroCaixa(models.Model):
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='lancamentos')
    tipo = models.CharField(max_length=10, choices=TipoLancamento.choices)
    origem = models.CharField(max_length=10, choices=OrigemLancamento.choices)
    origem_id = models.PositiveIntegerField(null=True, blank=True)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data = models.DateField()
    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_atual = models.DecimalField(max_digits=12, decimal_places=2)
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )
    estornado = models.BooleanField(default=False)
    estorno_de = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='estornos',
    )

    class Meta:
        db_table = 'fin_livro_caixa'
        ordering = ['-data', '-criado_em']

    def __str__(self):
        return f'{self.get_tipo_display()} R$ {self.valor} — {self.descricao}'


# --- Conciliacao Bancaria ---

class StatusConciliacao(models.TextChoices):
    PENDENTE         = 'PENDENTE',         'Pendente'
    PROCESSADO       = 'PROCESSADO',       'Processado'
    COM_DIVERGENCIAS = 'COM_DIVERGENCIAS', 'Com Divergencias'


class ConciliacaoExtrato(BaseModel):
    conta         = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='conciliacoes')
    arquivo_nome  = models.CharField(max_length=500)
    periodo       = models.DateField()
    processado_em = models.DateTimeField(auto_now_add=True)
    status        = models.CharField(
        max_length=20, choices=StatusConciliacao.choices, default='PENDENTE',
    )
    total_banco   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_sistema = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    divergencias  = models.IntegerField(default=0)
    criado_por    = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'fin_conciliacao_extrato'
        ordering = ['-processado_em']

    def __str__(self):
        return f'Conciliacao {self.conta.nome} — {self.periodo.strftime("%m/%Y")}'


class StatusItemConciliacao(models.TextChoices):
    CONCILIADO       = 'CONCILIADO',       'Conciliado'
    FALTANDO_SISTEMA = 'FALTANDO_SISTEMA', 'Faltando no Sistema'
    FALTANDO_BANCO   = 'FALTANDO_BANCO',   'Faltando no Banco'


class ItemConciliacao(models.Model):
    conciliacao     = models.ForeignKey(
        ConciliacaoExtrato, on_delete=models.CASCADE, related_name='itens',
    )
    data_banco      = models.DateField()
    descricao_banco = models.CharField(max_length=500)
    valor           = models.DecimalField(max_digits=12, decimal_places=2)
    tipo            = models.CharField(max_length=10, choices=TipoLancamento.choices)
    status          = models.CharField(max_length=20, choices=StatusItemConciliacao.choices)
    lancamento_lc   = models.ForeignKey(
        LivroCaixa, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='conciliacoes',
    )
    confirmado      = models.BooleanField(default=False)

    class Meta:
        db_table = 'fin_item_conciliacao'
        ordering = ['data_banco']

    def __str__(self):
        return f'{self.data_banco} {self.tipo} R${self.valor} — {self.status}'


class NaturezaPadraoConciliacao(models.TextChoices):
    APORTE             = 'APORTE',             'Aporte (capital social)'
    RECEITA_FINANCEIRA = 'RECEITA_FINANCEIRA', 'Receita Financeira (rendimento)'


class PadraoSeguroConciliacao(models.Model):
    descricao_padrao = models.CharField(max_length=300)
    tipo             = models.CharField(max_length=10, choices=TipoLancamento.choices)
    natureza         = models.CharField(
        max_length=20,
        choices=NaturezaPadraoConciliacao.choices,
        default='APORTE',
        help_text='Apenas para tipo=ENTRADA: APORTE vai para PL; RECEITA_FINANCEIRA entra no DRE.',
    )
    ativo            = models.BooleanField(default=True)
    criado_em        = models.DateTimeField(auto_now_add=True)
    criado_por       = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'fin_padrao_seguro_conciliacao'
        ordering = ['tipo', 'descricao_padrao']

    def __str__(self):
        return f'[{self.tipo}] {self.descricao_padrao}'
