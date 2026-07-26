from rest_framework import serializers

from .models import Cobranca, MetodoPagamento, Parcela


class MetodoPagamentoSerializer(serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    nome_display = serializers.CharField(source='get_nome_display', read_only=True)

    class Meta:
        model = MetodoPagamento
        fields = ['id', 'nome', 'nome_display', 'ativo', 'is_active', 'created_at']
        read_only_fields = ['id', 'nome_display', 'created_at']


class CobrancaSerializer(serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    cliente_nome = serializers.CharField(source='cliente.nome_razao_social', read_only=True)
    metodo_nome  = serializers.CharField(
        source='metodo.get_nome_display', read_only=True, allow_null=True,
    )
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Cobranca
        fields = [
            'id', 'cliente', 'cliente_nome', 'descricao', 'valor',
            'vencimento', 'status', 'status_label', 'metodo', 'metodo_nome',
            'data_pagamento', 'comprovante', 'observacoes', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'cliente_nome', 'metodo_nome', 'status_label', 'is_active', 'created_at']


class ParcelaSerializer(serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Parcela
        fields = [
            'id', 'cobranca', 'numero', 'valor', 'vencimento',
            'status', 'status_label', 'data_pagamento', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'status_label', 'created_at']
