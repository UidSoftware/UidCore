from django.db.models import Q
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from accounts.models import PerfilUsuario
from common.mixins import AuditMixin

from .models import Agenda, Compromisso
from .serializers import AgendaSerializer, CompromissoSerializer


class AgendaViewSet(AuditMixin, ModelViewSet):
    serializer_class = AgendaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nome']
    # permission_classes: SEM mudanca (continua IsAuthenticated puro) --
    # restringir quebraria OPERACIONAL/MARKETING, que hoje gerenciam
    # agendas livremente (sem staffOnly no Sidebar). Regra do PROFISSIONAL
    # e so de ESCOPO DE DADOS (get_queryset), nao de permissao de entrada
    # (Manutencao 63, RF-07).

    def get_queryset(self):
        qs = Agenda.objects.filter(is_active=True).order_by('nome')
        u = self.request.user
        if u.perfil == PerfilUsuario.PROFISSIONAL and not u.tem_acesso_total:
            qs = qs.filter(Q(profissional=u) | Q(created_by=u))
        return qs


class CompromissoViewSet(AuditMixin, ModelViewSet):
    serializer_class = CompromissoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['agenda', 'status', 'cliente']
    search_fields = ['titulo', 'descricao']
    ordering_fields = ['inicio', 'fim']
    # permission_classes: idem AgendaViewSet -- sem mudanca (Manutencao 63, RF-08).

    def get_queryset(self):
        qs = (
            Compromisso.objects.filter(is_active=True)
            .select_related('agenda', 'cliente')
            .order_by('inicio')
        )
        u = self.request.user
        if u.perfil == PerfilUsuario.PROFISSIONAL and not u.tem_acesso_total:
            qs = qs.filter(Q(created_by=u) | Q(agenda__profissional=u))
        return qs
