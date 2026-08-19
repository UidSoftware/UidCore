from decimal import Decimal

from rest_framework import serializers

from .models import Aporte, Categoria, Conta, Despesa, EstornoReceita, LivroCaixa, Receita


class CategoriaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = Categoria
        fields = ['id', 'nome', 'tipo', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class ContaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    saldo_atual = serializers.SerializerMethodField()

    class Meta:
        model = Conta
        fields = [
            'id', 'nome', 'tipo', 'banco', 'agencia', 'numero',
            'saldo_inicial', 'saldo_atual', 'is_active', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_saldo_atual(self, obj):
        from .services import saldo_real
        return saldo_real(obj)


class AporteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)

    class Meta:
        model = Aporte
        fields = [
            'id', 'tipo', 'descricao', 'valor', 'conta', 'conta_nome',
            'data', 'responsavel', 'observacoes', 'is_active', 'created_at',
        ]
        read_only_fields = ['created_at']


class ReceitaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    cliente_nome = serializers.CharField(source='cliente.nome_razao_social', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)

    class Meta:
        model = Receita
        fields = [
            'id', 'tipo', 'descricao',
            'cliente', 'cliente_nome',
            'categoria', 'categoria_nome',
            'valor_bruto', 'desconto', 'valor_liquido',
            'conta', 'conta_nome',
            'vencimento', 'recebimento', 'status',
            'referencia_mes', 'observacoes', 'is_active', 'created_at',
        ]
        read_only_fields = ['valor_liquido', 'created_at']

    def validate(self, data):
        bruto = data.get('valor_bruto', getattr(self.instance, 'valor_bruto', Decimal('0')))
        desconto = data.get('desconto', getattr(self.instance, 'desconto', Decimal('0')))
        if desconto > bruto:
            raise serializers.ValidationError({'desconto': 'Desconto não pode ser maior que o valor bruto.'})
        return data


class DespesaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)

    class Meta:
        model = Despesa
        fields = [
            'id', 'tipo', 'descricao', 'fornecedor',
            'valor_bruto', 'desconto', 'valor_liquido',
            'conta', 'conta_nome',
            'categoria', 'categoria_nome',
            'vencimento', 'pagamento', 'forma_pagamento', 'status',
            'referencia_mes', 'comprovante', 'observacoes',
            'recorrente', 'frequencia', 'quantidade',
            'estornado', 'data_estorno', 'motivo_estorno',
            'is_active', 'created_at',
        ]
        read_only_fields = ['valor_liquido', 'estornado', 'data_estorno', 'motivo_estorno', 'created_at']

    def validate(self, data):
        bruto = data.get('valor_bruto', getattr(self.instance, 'valor_bruto', Decimal('0')))
        desconto = data.get('desconto', getattr(self.instance, 'desconto', Decimal('0')))
        if desconto > bruto:
            raise serializers.ValidationError({'desconto': 'Desconto não pode ser maior que o valor bruto.'})
        return data


class LivroCaixaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)
    tipo_label = serializers.CharField(source='get_tipo_display', read_only=True)
    origem_label = serializers.CharField(source='get_origem_display', read_only=True)

    class Meta:
        model = LivroCaixa
        fields = [
            'id', 'conta', 'conta_nome',
            'tipo', 'tipo_label', 'origem', 'origem_label', 'origem_id',
            'descricao', 'valor', 'data',
            'saldo_anterior', 'saldo_atual',
            'criado_em', 'estornado', 'estorno_de',
        ]
        read_only_fields = [
            'criado_em', 'saldo_anterior', 'saldo_atual', 'estornado', 'estorno_de',
        ]


class EstornoReceitaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = EstornoReceita
        fields = ['id', 'receita', 'valor', 'motivo', 'data_estorno', 'item_venda', 'created_at']
        read_only_fields = ['id', 'created_at']


# --- Conciliacao Bancaria ---

from .models import ConciliacaoExtrato, ItemConciliacao, PadraoSeguroConciliacao


class ConciliacaoExtratoSerializer(serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    conta_nome   = serializers.CharField(source='conta.nome', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ConciliacaoExtrato
        fields = [
            'id', 'conta', 'conta_nome', 'arquivo_nome', 'periodo',
            'processado_em', 'status', 'status_label',
            'total_banco', 'total_sistema', 'divergencias',
        ]
        read_only_fields = [
            'id', 'conta_nome', 'processado_em', 'status', 'status_label',
            'total_banco', 'total_sistema', 'divergencias',
        ]


class ItemConciliacaoSerializer(serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    tipo_label   = serializers.CharField(source='get_tipo_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ItemConciliacao
        fields = [
            'id', 'conciliacao', 'data_banco', 'descricao_banco',
            'valor', 'tipo', 'tipo_label', 'status', 'status_label',
            'lancamento_lc', 'confirmado', 'is_active', 'created_at',
        ]
        read_only_fields = ['created_at']


class PadraoSeguroConciliacaoSerializer(serializers.ModelSerializer):
    id             = serializers.IntegerField(source='pk', read_only=True)
    tipo_label     = serializers.CharField(source='get_tipo_display', read_only=True)
    natureza_label = serializers.CharField(source='get_natureza_display', read_only=True)

    class Meta:
        model = PadraoSeguroConciliacao
        fields = [
            'id', 'descricao_padrao', 'tipo', 'tipo_label',
            'natureza', 'natureza_label', 'is_active', 'created_at',
        ]
        read_only_fields = ['created_at']
