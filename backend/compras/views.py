from datetime import date

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from common.permissions import IsAdmin
from produtos.models import MovimentoEstoque, TipoMovimento

from .models import Compra, StatusCompra
from .serializers import CompraSerializer, CompraStatusUpdateSerializer


class CompraViewSet(ModelViewSet):
    queryset = (
        Compra.objects.filter(is_active=True)
        .select_related('fornecedor', 'conta', 'despesa')
        .prefetch_related('itens__produto')
    )
    permission_classes = [IsAdmin]  # RN-08 — Compra tem efeito financeiro direto
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'fornecedor', 'conta']
    search_fields = ['numero_nota_fiscal', 'fornecedor__nome_razao_social']
    ordering_fields = ['data_emissao', 'valor_total', 'status']
    # RN-05: Compra e ItemCompra sao imutaveis apos criacao, exceto a
    # transicao de status (RF-08) — sem PUT, sem DELETE fisico.
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return CompraStatusUpdateSerializer
        return CompraSerializer

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])

    def update(self, request, *args, **kwargs):
        # PATCH parcial apenas (RF-08) — nunca PUT completo (http_method_names
        # ja bloqueia 'put', isso aqui é defesa extra caso alguém registre
        # rota manualmente).
        kwargs['partial'] = True
        response = super().update(request, *args, **kwargs)
        instance = self.get_object()
        return Response(CompraSerializer(instance).data, status=response.status_code)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        RF-10 — cancela uma Compra:
          1. bloqueia se já CANCELADO;
          2. reverte o estoque de cada item via MovimentoEstoque tipo=AJUSTE
             (quantidade negativa) — RN-03: recalcula o fator no momento
             do cancelamento, não reusa o fator gravado na compra original;
          3. estorna a Despesa vinculada (PAGO -> financeiro.services.
             estornar_despesa; PENDENTE -> soft delete simples, nunca
             existiu LivroCaixa pra essa Despesa);
          4. marca a Compra como CANCELADO.
        Tudo em transaction.atomic() — qualquer falha (ex: despesa já
        estornada) reverte a reversão de estoque também.
        """
        from financeiro.services import estornar_despesa

        compra = self.get_object()

        if compra.status == StatusCompra.CANCELADO:
            return Response(
                {'detail': 'Compra já está cancelada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        motivo = request.data.get('motivo') or f'Compra #{compra.id} cancelada'

        with transaction.atomic():
            for item in compra.itens.select_related('produto').all():
                MovimentoEstoque.objects.create(
                    produto=item.produto,
                    tipo=TipoMovimento.AJUSTE,
                    quantidade=-item.quantidade,
                    unidade=item.unidade,
                    observacoes=f'Cancelamento Compra #{compra.id}',
                )

            despesa = compra.despesa
            if despesa is not None:
                if despesa.status == 'PAGO':
                    # Extraida de DespesaViewSet.estornar_despesa (secao 6.3
                    # da Especificacao) — levanta rest_framework.exceptions.
                    # ValidationError em caso de erro, que borbulha ate o
                    # dispatch do DRF (400) e desfaz TODA a transacao,
                    # inclusive a reversao de estoque já feita acima.
                    estornar_despesa(
                        despesa, motivo=motivo,
                        data_estorno=date.today(), usuario=request.user,
                    )
                elif despesa.status == 'PENDENTE':
                    despesa.is_active = False
                    despesa.save(update_fields=['is_active', 'updated_at'])

            compra.status = StatusCompra.CANCELADO
            compra.save()

        compra.refresh_from_db()
        return Response(CompraSerializer(compra).data)
