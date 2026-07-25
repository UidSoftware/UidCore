from rest_framework import serializers

from .models import ItemPedido, Orcamento, Pedido


class OrcamentoSerializer(serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    cliente_nome = serializers.CharField(source='cliente.nome_razao_social', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Orcamento
        fields = [
            'id', 'numero', 'cliente', 'cliente_nome', 'descricao',
            'valor_total', 'status', 'status_label', 'validade',
            'observacoes', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'numero', 'cliente_nome', 'status_label', 'created_at']


class PedidoSerializer(serializers.ModelSerializer):
    id               = serializers.IntegerField(source='pk', read_only=True)
    cliente_nome     = serializers.CharField(source='cliente.nome_razao_social', read_only=True)
    status_label     = serializers.CharField(source='get_status_display', read_only=True)
    orcamento_numero = serializers.CharField(
        source='orcamento.numero', read_only=True, allow_null=True,
    )

    class Meta:
        model = Pedido
        fields = [
            'id', 'numero', 'cliente', 'cliente_nome', 'orcamento', 'orcamento_numero',
            'status', 'status_label', 'valor_total', 'data_pedido',
            'data_entrega_prevista', 'observacoes', 'is_active', 'created_at',
        ]
        read_only_fields = [
            'id', 'numero', 'cliente_nome', 'status_label', 'orcamento_numero', 'created_at',
        ]


class ItemPedidoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = ItemPedido
        fields = [
            'id', 'pedido', 'descricao', 'quantidade',
            'valor_unitario', 'valor_total', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'valor_total', 'created_at']
