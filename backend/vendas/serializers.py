from rest_framework import serializers

from .models import ItemOrcamento, ItemPedido, Orcamento, Pedido


class ItemOrcamentoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    produto_nome = serializers.CharField(source='produto.nome', read_only=True, allow_null=True)

    class Meta:
        model = ItemOrcamento
        fields = [
            'id', 'produto', 'produto_nome', 'descricao',
            'quantidade', 'valor_unitario', 'valor_total',
            'is_active', 'created_at',
        ]
        read_only_fields = ['valor_total', 'created_at']


class OrcamentoSerializer(serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    cliente_nome = serializers.CharField(source='cliente.nome_razao_social', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    itens        = ItemOrcamentoSerializer(many=True, read_only=True)

    class Meta:
        model = Orcamento
        fields = [
            'id', 'numero', 'cliente', 'cliente_nome', 'descricao',
            'valor_total', 'status', 'status_label', 'validade',
            'observacoes', 'is_active', 'created_at',
            'itens',
        ]
        read_only_fields = ['id', 'numero', 'cliente_nome', 'status_label', 'created_at']


class ItemPedidoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    produto_nome = serializers.CharField(source='produto.nome', read_only=True, allow_null=True)

    class Meta:
        model = ItemPedido
        fields = [
            'id', 'pedido', 'produto', 'produto_nome', 'descricao',
            'quantidade', 'valor_unitario', 'valor_total',
            'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'valor_total', 'created_at']


class PedidoSerializer(serializers.ModelSerializer):
    id               = serializers.IntegerField(source='pk', read_only=True)
    cliente_nome     = serializers.CharField(source='cliente.nome_razao_social', read_only=True)
    status_label     = serializers.CharField(source='get_status_display', read_only=True)
    orcamento_numero = serializers.CharField(
        source='orcamento.numero', read_only=True, allow_null=True,
    )
    itens            = ItemPedidoSerializer(many=True, read_only=True)

    class Meta:
        model = Pedido
        fields = [
            'id', 'numero', 'cliente', 'cliente_nome', 'orcamento', 'orcamento_numero',
            'status', 'status_label', 'valor_total', 'data_pedido',
            'data_entrega_prevista', 'observacoes', 'is_active', 'created_at',
            'itens',
        ]
        read_only_fields = [
            'id', 'numero', 'cliente_nome', 'status_label', 'orcamento_numero', 'created_at',
        ]
