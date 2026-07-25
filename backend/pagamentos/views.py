from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .models import Cobranca, MetodoPagamento, Parcela
from .serializers import CobrancaSerializer, MetodoPagamentoSerializer, ParcelaSerializer


class MetodoPagamentoViewSet(ModelViewSet):
    queryset = MetodoPagamento.objects.filter(is_active=True).order_by('nome')
    serializer_class = MetodoPagamentoSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CobrancaViewSet(ModelViewSet):
    queryset = (
        Cobranca.objects.filter(is_active=True)
        .select_related('cliente', 'metodo')
        .order_by('vencimento')
    )
    serializer_class = CobrancaSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'cliente', 'metodo']
    search_fields = ['descricao']
    ordering_fields = ['vencimento', 'valor']

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ParcelaViewSet(ModelViewSet):
    queryset = Parcela.objects.filter(is_active=True).select_related('cobranca').order_by('numero')
    serializer_class = ParcelaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cobranca', 'status']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
