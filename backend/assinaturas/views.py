"""
assinaturas/views.py — Manutencao #64 [NUCLEO 3/5].

RN-07 — transições de status válidas: ATIVA <-> PAUSADA (pausar/retomar),
ATIVA -> ENCERRADA, PAUSADA -> ENCERRADA. ENCERRADA é estado terminal —
nenhuma action admite saída dela.
"""
from datetime import datetime

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from common.mixins import AuditMixin
from common.permissions import IsAdmin, IsFinanceiro

from .models import Assinatura, Plano, StatusAssinatura
from .serializers import AssinaturaSerializer, PlanoSerializer


class PlanoViewSet(AuditMixin, ModelViewSet):
    queryset = Plano.objects.filter(is_active=True).select_related('categoria')
    serializer_class = PlanoSerializer
    permission_classes = [IsAdmin | IsFinanceiro]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['periodicidade', 'ativo', 'categoria']
    search_fields = ['nome']
    ordering_fields = ['nome', 'valor']


class AssinaturaViewSet(AuditMixin, ModelViewSet):
    queryset = (
        Assinatura.objects.filter(is_active=True)
        .select_related('cliente', 'plano', 'conta')
    )
    serializer_class = AssinaturaSerializer
    permission_classes = [IsAdmin | IsFinanceiro]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'cliente', 'plano', 'conta']
    search_fields = ['cliente__nome_razao_social', 'plano__nome']
    ordering_fields = ['data_inicio', 'valor', 'status']

    @action(detail=True, methods=['post'])
    def encerrar(self, request, pk=None):
        """RF-04 — body: {data_fim, motivo}. Idempotente: já ENCERRADA -> 400."""
        assinatura = self.get_object()

        if assinatura.status == StatusAssinatura.ENCERRADA:
            return Response(
                {'detail': 'Assinatura já está encerrada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data_fim_raw = request.data.get('data_fim')
        if not data_fim_raw:
            return Response(
                {'data_fim': 'Campo obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            data_fim = datetime.strptime(str(data_fim_raw), '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'data_fim': 'Formato inválido. Use AAAA-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if data_fim < assinatura.data_inicio:
            return Response(
                {'data_fim': 'Não pode ser anterior à data de início.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assinatura.status = StatusAssinatura.ENCERRADA
        assinatura.data_fim = data_fim
        assinatura.motivo_encerramento = request.data.get('motivo', '')
        assinatura.encerrada_em = timezone.now()
        assinatura.updated_by = request.user
        assinatura.save()

        return Response(AssinaturaSerializer(assinatura).data)

    @action(detail=True, methods=['post'])
    def pausar(self, request, pk=None):
        """RF-04 — bloqueado se ENCERRADA (RN-07, estado terminal)."""
        assinatura = self.get_object()

        if assinatura.status == StatusAssinatura.ENCERRADA:
            return Response(
                {'detail': 'Assinatura encerrada é estado terminal — não pode ser pausada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if assinatura.status == StatusAssinatura.PAUSADA:
            return Response(
                {'detail': 'Assinatura já está pausada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assinatura.status = StatusAssinatura.PAUSADA
        assinatura.updated_by = request.user
        assinatura.save()

        return Response(AssinaturaSerializer(assinatura).data)

    @action(detail=True, methods=['post'])
    def retomar(self, request, pk=None):
        """RF-04 — só permitido a partir de PAUSADA (RN-07)."""
        assinatura = self.get_object()

        if assinatura.status != StatusAssinatura.PAUSADA:
            return Response(
                {'detail': 'Só é possível retomar uma assinatura pausada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assinatura.status = StatusAssinatura.ATIVA
        assinatura.updated_by = request.user
        assinatura.save()

        return Response(AssinaturaSerializer(assinatura).data)
