from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .models import ItemPedido, Orcamento, Pedido
from .serializers import ItemPedidoSerializer, OrcamentoSerializer, PedidoSerializer


class OrcamentoViewSet(ModelViewSet):
    queryset = Orcamento.objects.filter(is_active=True).select_related('cliente').order_by('-created_at')
    serializer_class = OrcamentoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'cliente']
    search_fields = ['numero', 'descricao']
    ordering_fields = ['created_at', 'valor_total']

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PedidoViewSet(ModelViewSet):
    queryset = (
        Pedido.objects.filter(is_active=True)
        .select_related('cliente', 'orcamento')
        .order_by('-created_at')
    )
    serializer_class = PedidoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'cliente']
    search_fields = ['numero']
    ordering_fields = ['created_at', 'data_pedido', 'valor_total']

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


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
