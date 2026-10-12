from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import AuditMixin

from .models import Agenda, Compromisso
from .serializers import AgendaSerializer, CompromissoSerializer


class AgendaViewSet(AuditMixin, ModelViewSet):
    queryset = Agenda.objects.filter(is_active=True).order_by('nome')
    serializer_class = AgendaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nome']


class CompromissoViewSet(AuditMixin, ModelViewSet):
    queryset = (
        Compromisso.objects.filter(is_active=True)
        .select_related('agenda', 'cliente')
        .order_by('inicio')
    )
    serializer_class = CompromissoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['agenda', 'status', 'cliente']
    search_fields = ['titulo', 'descricao']
    ordering_fields = ['inicio', 'fim']
