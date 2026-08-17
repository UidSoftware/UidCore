from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import ConversaoUnidade, EntradaEstoque, Produto, UnidadeBase
from .services import validar_cadeia


class ConversaoUnidadeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    unidade_display = serializers.CharField(source='get_unidade_display', read_only=True)
    converte_para_display = serializers.SerializerMethodField()

    class Meta:
        model = ConversaoUnidade
        fields = [
            'id', 'unidade', 'unidade_display',
            'converte_para', 'converte_para_display',
            'quantidade_por_base', 'is_active', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_converte_para_display(self, obj):
        if not obj.converte_para:
            return None
        return dict(UnidadeBase.choices).get(obj.converte_para, obj.converte_para)

    def validate(self, attrs):
        # RN-01/RN-03: valida a cadeia ANTES de salvar — não só no uso
        # posterior (EntradaEstoque/PDV). `produto` vem do contexto (create,
        # via views.py) ou da instância já persistida (edição via PATCH).
        produto = self.context.get('produto') or getattr(self.instance, 'produto', None)
        if produto is None:
            return attrs

        unidade = attrs.get('unidade', getattr(self.instance, 'unidade', None))
        converte_para = (
            attrs['converte_para'] if 'converte_para' in attrs
            else getattr(self.instance, 'converte_para', None)
        )
        quantidade_por_base = attrs.get(
            'quantidade_por_base', getattr(self.instance, 'quantidade_por_base', None),
        )
        excluir_id = self.instance.pk if self.instance else None

        try:
            validar_cadeia(
                produto, unidade, converte_para, quantidade_por_base,
                excluir_id=excluir_id,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({
                'unidade': exc.messages if hasattr(exc, 'messages') else [str(exc)],
            })
        return attrs


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
    conversoes = serializers.SerializerMethodField()

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

    def get_conversoes(self, obj):
        # CA-03: conversão soft-deletada (is_active=False) nunca pode
        # aparecer aqui — mesmo filtro do endpoint dedicado
        # GET /produtos/{id}/conversoes/. Se a queryset já veio com
        # Prefetch filtrado (ProdutoViewSet.get_queryset()), filtra em
        # Python pra reaproveitar o cache; senão faz o .filter() direto.
        if 'conversoes' in getattr(obj, '_prefetched_objects_cache', {}):
            conversoes = [c for c in obj.conversoes.all() if c.is_active]
        else:
            conversoes = obj.conversoes.filter(is_active=True)
        return ConversaoUnidadeSerializer(conversoes, many=True).data
