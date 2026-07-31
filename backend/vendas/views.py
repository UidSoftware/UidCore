from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .models import ItemOrcamento, ItemPedido, Orcamento, Pedido
from .serializers import ItemOrcamentoSerializer, ItemPedidoSerializer, OrcamentoSerializer, PedidoSerializer


class OrcamentoViewSet(ModelViewSet):
    serializer_class = OrcamentoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'cliente']
    search_fields = ['numero', 'descricao']
    ordering_fields = ['created_at', 'valor_total']

    def get_queryset(self):
        return (
            Orcamento.objects.filter(is_active=True)
            .select_related('cliente')
            .prefetch_related('itens__produto')
            .order_by('-created_at')
        )

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'], url_path='itens')
    def itens(self, request, pk=None):
        orcamento = self.get_object()
        if request.method == 'GET':
            qs = ItemOrcamento.objects.filter(orcamento=orcamento, is_active=True).select_related('produto')
            return Response(ItemOrcamentoSerializer(qs, many=True).data)
        serializer = ItemOrcamentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(orcamento=orcamento)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'itens/(?P<item_id>\d+)')
    def item_detalhe(self, request, pk=None, item_id=None):
        orcamento = self.get_object()
        try:
            item = ItemOrcamento.objects.get(pk=item_id, orcamento=orcamento, is_active=True)
        except ItemOrcamento.DoesNotExist:
            return Response({'detail': 'Item não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'DELETE':
            item.is_active = False
            item.save(update_fields=['is_active', 'updated_at'])
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = ItemOrcamentoSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PedidoViewSet(ModelViewSet):
    serializer_class = PedidoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'cliente']
    search_fields = ['numero']
    ordering_fields = ['created_at', 'data_pedido', 'valor_total']

    def get_queryset(self):
        return (
            Pedido.objects.filter(is_active=True)
            .select_related('cliente', 'orcamento')
            .prefetch_related('itens__produto')
            .order_by('-created_at')
        )

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'], url_path='itens')
    def itens(self, request, pk=None):
        pedido = self.get_object()
        if request.method == 'GET':
            qs = ItemPedido.objects.filter(pedido=pedido, is_active=True).select_related('produto')
            return Response(ItemPedidoSerializer(qs, many=True).data)
        serializer = ItemPedidoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(pedido=pedido)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'itens/(?P<item_id>\d+)')
    def item_detalhe(self, request, pk=None, item_id=None):
        pedido = self.get_object()
        try:
            item = ItemPedido.objects.get(pk=item_id, pedido=pedido, is_active=True)
        except ItemPedido.DoesNotExist:
            return Response({'detail': 'Item não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'DELETE':
            item.is_active = False
            item.save(update_fields=['is_active', 'updated_at'])
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = ItemPedidoSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ItemPedidoViewSet(ModelViewSet):
    queryset = ItemPedido.objects.filter(is_active=True).select_related('pedido').order_by('id')
    serializer_class = ItemPedidoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['pedido']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
