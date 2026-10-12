from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import AuditMixin

from .models import Cobranca, MetodoPagamento, Parcela
from .serializers import CobrancaSerializer, MetodoPagamentoSerializer, ParcelaSerializer


class MetodoPagamentoViewSet(AuditMixin, ModelViewSet):
    queryset = MetodoPagamento.objects.filter(is_active=True).order_by('nome')
    serializer_class = MetodoPagamentoSerializer


class CobrancaViewSet(AuditMixin, ModelViewSet):
    queryset = (
        Cobranca.objects.filter(is_active=True)
        .select_related('cliente', 'metodo')
        .order_by('vencimento')
    )
    serializer_class = CobrancaSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'cliente', 'metodo']
    search_fields = ['descricao']
    ordering_fields = ['vencimento', 'valor']


class ParcelaViewSet(AuditMixin, ModelViewSet):
    queryset = Parcela.objects.filter(is_active=True).select_related('cobranca').order_by('numero')
    serializer_class = ParcelaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cobranca', 'status']
