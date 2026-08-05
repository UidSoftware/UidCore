"""
pdv/serializers.py

RNF-04: id = serializers.IntegerField(source='pk', read_only=True) é o
PRIMEIRO campo de TODOS os serializers (padrão obrigatório Uid Software).
"""
from decimal import Decimal

from rest_framework import serializers

from .models import (
    ItemVenda,
    MovimentoCaixa,
    PagamentoVenda,
    RecebivelCartao,
    SessaoCaixa,
    Venda,
)


# ---------------------------------------------------------------------------
# MovimentoCaixa
# ---------------------------------------------------------------------------

class MovimentoCaixaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    tipo_label = serializers.CharField(source='get_tipo_display', read_only=True)
    operador_nome = serializers.CharField(source='operador.get_full_name', read_only=True)

    class Meta:
        model = MovimentoCaixa
        fields = [
            'id', 'sessao', 'tipo', 'tipo_label', 'valor', 'motivo',
            'operador', 'operador_nome', 'data_hora', 'is_active', 'created_at',
        ]
        read_only_fields = ['data_hora', 'created_at']


# ---------------------------------------------------------------------------
# SessaoCaixa
# ---------------------------------------------------------------------------

class SessaoCaixaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)
    operador_nome = serializers.CharField(source='operador.get_full_name', read_only=True)
    movimentos = MovimentoCaixaSerializer(many=True, read_only=True)

    class Meta:
        model = SessaoCaixa
        fields = [
            'id', 'conta', 'conta_nome', 'operador', 'operador_nome',
            'valor_abertura', 'data_abertura', 'data_fechamento',
            'valor_fechamento_informado', 'valor_fechamento_calculado',
            'diferenca', 'status', 'status_label', 'observacoes',
            'movimentos', 'is_active', 'created_at',
        ]
        read_only_fields = [
            'data_abertura', 'data_fechamento',
            'valor_fechamento_calculado', 'diferenca', 'created_at',
        ]


class AbrirSessaoSerializer(serializers.Serializer):
    conta = serializers.IntegerField()
    valor_abertura = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)


class FecharSessaoSerializer(serializers.Serializer):
    valor_fechamento_informado = serializers.DecimalField(max_digits=12, decimal_places=2)
    observacoes = serializers.CharField(required=False, allow_blank=True, default='')


class MovimentoSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=['SANGRIA', 'SUPRIMENTO'])
    valor = serializers.DecimalField(max_digits=12, decimal_places=2)
    motivo = serializers.CharField()


# ---------------------------------------------------------------------------
# ItemVenda
# ---------------------------------------------------------------------------

class ItemVendaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    produto_nome = serializers.CharField(source='produto.nome', read_only=True)
    produto_codigo_barras = serializers.CharField(source='produto.codigo_barras', read_only=True)

    class Meta:
        model = ItemVenda
        fields = [
            'id', 'venda', 'produto', 'produto_nome', 'produto_codigo_barras',
            'quantidade', 'unidade', 'valor_unitario', 'desconto_item',
            'valor_total', 'quantidade_estornada', 'is_active', 'created_at',
        ]
        read_only_fields = ['valor_unitario', 'valor_total', 'quantidade_estornada', 'created_at']


class AdicionarItemSerializer(serializers.Serializer):
    produto = serializers.IntegerField()
    quantidade = serializers.DecimalField(max_digits=12, decimal_places=3)
    unidade = serializers.CharField(max_length=2)
    desconto_item = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)


class EditarItemSerializer(serializers.Serializer):
    quantidade = serializers.DecimalField(max_digits=12, decimal_places=3, required=False)
    desconto_item = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class DevolverItemSerializer(serializers.Serializer):
    quantidade = serializers.DecimalField(max_digits=12, decimal_places=3)
    motivo = serializers.CharField()
    pagamento_id = serializers.IntegerField()


# ---------------------------------------------------------------------------
# PagamentoVenda
# ---------------------------------------------------------------------------

class PagamentoVendaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    metodo_nome = serializers.CharField(source='metodo.get_nome_display', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)

    class Meta:
        model = PagamentoVenda
        fields = [
            'id', 'venda', 'metodo', 'metodo_nome', 'valor',
            'conta', 'conta_nome', 'receita', 'is_active', 'created_at',
        ]
        read_only_fields = ['receita', 'created_at']


class PagamentoPayloadSerializer(serializers.Serializer):
    """Representa uma entrada no array 'pagamentos' do payload de finalizar."""
    metodo = serializers.IntegerField()
    valor = serializers.DecimalField(max_digits=12, decimal_places=2)
    conta = serializers.IntegerField(required=False, allow_null=True)
    taxa_percentual = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        help_text='Obrigatorio para CARTAO_CREDITO.',
    )
    prazo_dias = serializers.IntegerField(
        required=False, default=0,
        help_text='Dias ate liquidacao. Obrigatorio para CARTAO_CREDITO.',
    )


class FinalizarVendaSerializer(serializers.Serializer):
    pagamentos = PagamentoPayloadSerializer(many=True)

    def validate_pagamentos(self, value):
        if not value:
            raise serializers.ValidationError('Pelo menos um pagamento e obrigatorio.')
        return value


class CancelarVendaSerializer(serializers.Serializer):
    motivo = serializers.CharField()


# ---------------------------------------------------------------------------
# Venda
# ---------------------------------------------------------------------------

class VendaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    cliente_nome = serializers.CharField(source='cliente.nome_razao_social', read_only=True)
    operador_nome = serializers.CharField(source='operador.get_full_name', read_only=True)
    sessao_conta_nome = serializers.CharField(source='sessao_caixa.conta.nome', read_only=True)
    itens = ItemVendaSerializer(many=True, read_only=True)
    pagamentos = PagamentoVendaSerializer(many=True, read_only=True)

    class Meta:
        model = Venda
        fields = [
            'id', 'numero', 'sessao_caixa', 'sessao_conta_nome',
            'cliente', 'cliente_nome',
            'operador', 'operador_nome',
            'status', 'status_label',
            'subtotal', 'desconto_total', 'valor_total',
            'data_hora', 'cancelada_em', 'motivo_cancelamento',
            'itens', 'pagamentos',
            'is_active', 'created_at',
        ]
        read_only_fields = [
            'numero', 'valor_total', 'subtotal', 'data_hora',
            'cancelada_em', 'motivo_cancelamento', 'created_at',
        ]


# ---------------------------------------------------------------------------
# RecebivelCartao
# ---------------------------------------------------------------------------

class RecebivelCartaoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = RecebivelCartao
        fields = [
            'id', 'pagamento', 'receita',
            'taxa_percentual', 'valor_bruto', 'valor_liquido_previsto',
            'data_prevista_liquidacao', 'data_liquidacao',
            'status', 'status_label',
            'is_active', 'created_at',
        ]
        read_only_fields = [
            'valor_liquido_previsto', 'data_liquidacao',
            'status', 'created_at',
        ]
