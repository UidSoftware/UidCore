from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import ConversaoUnidade, EntradaEstoque, Produto
from .serializers import ConversaoUnidadeSerializer, EntradaEstoqueSerializer, ProdutoSerializer


class ProdutoViewSet(ModelViewSet):
    serializer_class = ProdutoSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nome', 'codigo_barras']
    ordering_fields = ['nome', 'created_at', 'quantidade_estoque', 'preco_venda']
    ordering = ['nome']

    def get_queryset(self):
        return Produto.objects.filter(is_active=True).prefetch_related('conversoes')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'], url_path='conversoes')
    def conversoes(self, request, pk=None):
        produto = self.get_object()
        if request.method == 'GET':
            qs = ConversaoUnidade.objects.filter(produto=produto, is_active=True)
            return Response(ConversaoUnidadeSerializer(qs, many=True).data)
        serializer = ConversaoUnidadeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(produto=produto)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'conversoes/(?P<conv_id>\d+)')
    def conversao_detalhe(self, request, pk=None, conv_id=None):
        produto = self.get_object()
        try:
            conversao = ConversaoUnidade.objects.get(pk=conv_id, produto=produto, is_active=True)
        except ConversaoUnidade.DoesNotExist:
            return Response({'detail': 'Conversão não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'DELETE':
            conversao.is_active = False
            conversao.save(update_fields=['is_active', 'updated_at'])
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = ConversaoUnidadeSerializer(conversao, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], url_path='entradas')
    def entradas(self, request, pk=None):
        produto = self.get_object()
        if request.method == 'GET':
            qs = EntradaEstoque.objects.filter(produto=produto, is_active=True).order_by('-created_at')
            return Response(EntradaEstoqueSerializer(qs, many=True).data)
        serializer = EntradaEstoqueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(produto=produto, criado_por=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
