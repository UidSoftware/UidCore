from rest_framework import serializers

from .models import ConversaoUnidade, EntradaEstoque, Produto


class ConversaoUnidadeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    unidade_display = serializers.CharField(source='get_unidade_display', read_only=True)

    class Meta:
        model = ConversaoUnidade
        fields = ['id', 'unidade', 'unidade_display', 'quantidade_por_base', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class EntradaEstoqueSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    unidade_display = serializers.CharField(source='get_unidade_display', read_only=True)

    class Meta:
        model = EntradaEstoque
        fields = [
            'id', 'quantidade', 'unidade', 'unidade_display',
            'quantidade_base', 'nota_fiscal', 'observacoes',
            'is_active', 'created_at',
        ]
        read_only_fields = ['quantidade_base', 'created_at']


class ProdutoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    unidade_base_display = serializers.CharField(source='get_unidade_base_display', read_only=True)
    conversoes = ConversaoUnidadeSerializer(many=True, read_only=True)

    class Meta:
        model = Produto
        fields = [
            'id', 'nome', 'codigo_barras',
            'quantidade_estoque', 'estoque_minimo',
            'unidade_base', 'unidade_base_display',
            'valor_unitario', 'preco_venda',
            'observacoes', 'is_active', 'created_at', 'updated_at',
            'conversoes',
        ]
        read_only_fields = ['quantidade_estoque', 'created_at', 'updated_at']
