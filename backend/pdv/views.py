"""
pdv/views.py — ViewSets do módulo PDV.

Permissões (RF-16 / Seção 11 da spec / ADR-007):
  - IsAuthenticated : abrir/vender/sangria/suprimento/fechar caixa, devolver item
  - IsAdmin         : ReceitaViewSet.estornar já em financeiro (não aqui)
                      SessaoCaixaViewSet.list condicional (operador vê só as próprias)
"""
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from produtos.models import Produto, UnidadeBase
from produtos.services import fator_para_base

from .models import ItemVenda, MovimentoCaixa, PagamentoVenda, SessaoCaixa, Venda
from .serializers import (
    AbrirSessaoSerializer,
    AdicionarItemSerializer,
    CancelarVendaSerializer,
    DevolverItemSerializer,
    EditarItemSerializer,
    FecharSessaoSerializer,
    FinalizarVendaSerializer,
    ItemVendaSerializer,
    MovimentoCaixaSerializer,
    MovimentoSerializer,
    SessaoCaixaSerializer,
    VendaSerializer,
)
from .services import (
    abrir_sessao,
    cancelar_venda,
    devolver_item,
    fechar_sessao,
    finalizar_venda,
)


# ---------------------------------------------------------------------------
# SessaoCaixaViewSet
# ---------------------------------------------------------------------------

class SessaoCaixaViewSet(ModelViewSet):
    """
    Gerencia sessões de caixa.

    GET list: operador comum vê só as próprias; is_staff vê todas (RF-16).
    """
    serializer_class = SessaoCaixaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['conta', 'operador', 'status']
    ordering_fields = ['data_abertura']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = SessaoCaixa.objects.filter(is_active=True).select_related(
            'conta', 'operador',
        ).prefetch_related('movimentos')
        if not self.request.user.is_staff:
            qs = qs.filter(operador=self.request.user)
        return qs

    def create(self, request, *args, **kwargs):
        """POST /api/v1/pdv/sessoes/ — Abre sessão (RF-01 / RF-02)."""
        ser = AbrirSessaoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        sessao = abrir_sessao(
            conta_id=ser.validated_data['conta'],
            valor_abertura=ser.validated_data['valor_abertura'],
            usuario=request.user,
        )
        return Response(
            SessaoCaixaSerializer(sessao).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'], url_path='atual')
    def sessao_atual(self, request):
        """
        GET /api/v1/pdv/sessoes/atual/ — Sessão ABERTA do operador logado.
        Usado pelo gate de rota do Loom para redirecionar para abertura ou venda.
        """
        sessao = SessaoCaixa.objects.filter(
            operador=request.user, status='ABERTA', is_active=True,
        ).first()
        return Response({
            'sessao': SessaoCaixaSerializer(sessao).data if sessao else None,
        })

    @action(detail=True, methods=['post'], url_path='movimento')
    def movimento(self, request, pk=None):
        """
        POST /api/v1/pdv/sessoes/{id}/movimento/ — Sangria ou Suprimento (RF-10).
        """
        sessao = self.get_object()
        if sessao.status != 'ABERTA':
            return Response(
                {'status': 'Sessao nao esta aberta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = MovimentoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        mov = MovimentoCaixa.objects.create(
            sessao=sessao,
            tipo=d['tipo'],
            valor=d['valor'],
            motivo=d['motivo'],
            operador=request.user,
        )
        return Response(
            MovimentoCaixaSerializer(mov).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='fechar')
    def fechar(self, request, pk=None):
        """
        POST /api/v1/pdv/sessoes/{id}/fechar/ — Fecha sessão (RF-11 / RN-07).
        Nunca bloqueia por diferença.
        """
        sessao = self.get_object()
        ser = FecharSessaoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        sessao = fechar_sessao(
            sessao=sessao,
            valor_fechamento_informado=ser.validated_data['valor_fechamento_informado'],
            observacoes=ser.validated_data.get('observacoes', ''),
        )
        return Response(SessaoCaixaSerializer(sessao).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# VendaViewSet
# ---------------------------------------------------------------------------

class VendaViewSet(ModelViewSet):
    """
    Gerencia vendas do PDV.

    POST /api/v1/pdv/vendas/ — abre Venda ABERTA vinculada à sessão aberta.
    GET  /api/v1/pdv/vendas/{id}/ — detalhe com itens + pagamentos nested.
    """
    serializer_class = VendaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'operador', 'cliente', 'sessao_caixa']
    search_fields = ['numero']
    ordering_fields = ['data_hora', 'valor_total']
    # 'patch' necessário para:
    #   PATCH /vendas/{id}/ → partial_update (vincular/desvincular cliente)
    #   PATCH /vendas/{id}/itens/{item_id}/ → editar_item action
    # Sem 'patch' aqui o DRF bloqueia com 405 antes de rotear qualquer action.
    http_method_names = ['get', 'post', 'patch', 'head', 'options', 'delete']

    def get_queryset(self):
        return (
            Venda.objects.filter(is_active=True)
            .select_related('sessao_caixa__conta', 'cliente', 'operador')
            .prefetch_related('itens__produto', 'pagamentos__metodo', 'pagamentos__conta')
        )

    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /api/v1/pdv/vendas/{id}/ — apenas o campo `cliente` é editável
        diretamente (vincular/desvincular cliente na venda ABERTA).

        Todos os demais campos da Venda só mudam via actions dedicadas
        (finalizar, cancelar, movimento...). Whitelist explícita para impedir
        mutações acidentais de status, operador, sessao_caixa etc.
        """
        CAMPOS_EDITAVEIS = {'cliente'}
        payload = {k: v for k, v in request.data.items() if k in CAMPOS_EDITAVEIS}
        if not payload and 'cliente' not in request.data:
            return Response(
                {'detalhe': 'Nenhum campo editavel fornecido. Apenas "cliente" e permitido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Inclui explicitamente 'cliente' mesmo que seja null (desvincular)
        if 'cliente' in request.data:
            payload['cliente'] = request.data['cliente']
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Abre uma Venda ABERTA vinculada à sessão aberta do operador.
        RN-02: valida que o operador tem sessão ABERTA.
        """
        sessao = SessaoCaixa.objects.filter(
            operador=request.user, status='ABERTA', is_active=True,
        ).first()
        if not sessao:
            return Response(
                {'sessao_caixa': 'Nenhuma sessao de caixa aberta para este operador.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cliente_id = request.data.get('cliente')
        venda = Venda.objects.create(
            sessao_caixa=sessao,
            operador=request.user,
            cliente_id=cliente_id,
        )
        return Response(
            VendaSerializer(venda).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='itens')
    def adicionar_item(self, request, pk=None):
        """
        POST /api/v1/pdv/vendas/{id}/itens/ — adiciona item ao carrinho (RF-03/RF-04).

        RN-03: valor_unitario é sempre snapshot de Produto.preco_venda — nunca
        aceito do payload.
        """
        venda = self.get_object()
        if venda.status != 'ABERTA':
            return Response(
                {'status': 'Venda nao esta aberta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = AdicionarItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        try:
            produto = Produto.objects.get(pk=d['produto'], is_active=True)
        except Produto.DoesNotExist:
            return Response(
                {'produto': 'Produto nao encontrado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unidade = d['unidade']
        if unidade not in UnidadeBase.values:
            return Response(
                {'unidade': f'Unidade invalida: {unidade}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # RF-06/RN-04: valor_unitario segue sendo sempre snapshot calculado
        # pelo backend (nunca aceito do payload) — agora convertido pela
        # unidade escolhida quando != unidade_base do produto. RN-05: unidade
        # sem conversão cadastrada (direta ou em cadeia) retorna 400 legível,
        # nunca mais cobra o preço da unidade base por uma unidade maior.
        if unidade == produto.unidade_base:
            valor_unitario = produto.preco_venda
        else:
            try:
                fator = fator_para_base(produto, unidade)
            except DjangoValidationError as exc:
                return Response(
                    {'unidade': exc.messages if hasattr(exc, 'messages') else [str(exc)]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            valor_unitario = (produto.preco_venda * fator).quantize(Decimal('0.01'))

        item = ItemVenda.objects.create(
            venda=venda,
            produto=produto,
            quantidade=d['quantidade'],
            unidade=unidade,
            valor_unitario=valor_unitario,  # RN-03/RN-04: snapshot calculado pelo backend
            desconto_item=d['desconto_item'],
        )
        venda.recalcular_total()
        return Response(
            ItemVendaSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['patch'], url_path=r'itens/(?P<item_id>\d+)')
    def editar_item(self, request, pk=None, item_id=None):
        """
        PATCH /api/v1/pdv/vendas/{id}/itens/{item_id}/ — edita item do carrinho.
        Apenas em venda ABERTA.
        """
        venda = self.get_object()
        if venda.status != 'ABERTA':
            return Response(
                {'status': 'Venda nao esta aberta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item = get_object_or_404(ItemVenda, pk=item_id, venda=venda, is_active=True)
        ser = EditarItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        if 'quantidade' in d:
            item.quantidade = d['quantidade']
        if 'desconto_item' in d:
            item.desconto_item = d['desconto_item']
        item.save()
        venda.recalcular_total()
        return Response(ItemVendaSerializer(item).data)

    @action(detail=True, methods=['delete'], url_path=r'itens/(?P<item_id>\d+)/remover')
    def remover_item(self, request, pk=None, item_id=None):
        """
        DELETE /api/v1/pdv/vendas/{id}/itens/{item_id}/ — remove item do carrinho.
        Soft delete. Apenas em venda ABERTA.
        """
        venda = self.get_object()
        if venda.status != 'ABERTA':
            return Response(
                {'status': 'Venda nao esta aberta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item = get_object_or_404(ItemVenda, pk=item_id, venda=venda, is_active=True)
        item.is_active = False
        item.save(update_fields=['is_active', 'updated_at'])
        venda.recalcular_total()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='finalizar')
    def finalizar(self, request, pk=None):
        """
        POST /api/v1/pdv/vendas/{id}/finalizar/ — Finaliza venda (RF-06..RF-09).
        """
        venda = self.get_object()
        ser = FinalizarVendaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        venda = finalizar_venda(
            venda=venda,
            pagamentos_payload=ser.validated_data['pagamentos'],
            usuario=request.user,
        )
        # Limpa o cache de prefetch gravado pelo get_object() antes de qualquer
        # PagamentoVenda existir. Sem isso, VendaSerializer leria pagamentos: []
        # do cache stale mesmo com os dados certos já no banco (RF-07 / Sentinel).
        venda._prefetched_objects_cache = {}
        return Response(VendaSerializer(venda).data)

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        """
        POST /api/v1/pdv/vendas/{id}/cancelar/ — Cancela venda (RF-12 / RN-08).
        """
        venda = self.get_object()
        ser = CancelarVendaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        venda = cancelar_venda(
            venda=venda,
            motivo=ser.validated_data['motivo'],
            usuario=request.user,
        )
        # Mesmo padrão de finalizar: limpa cache de prefetch stale antes de
        # serializar, garantindo que itens/pagamentos reflitam o estado pós-mutação.
        venda._prefetched_objects_cache = {}
        return Response(VendaSerializer(venda).data)

    @action(detail=True, methods=['post'], url_path=r'itens/(?P<item_id>\d+)/devolver')
    def devolver(self, request, pk=None, item_id=None):
        """
        POST /api/v1/pdv/vendas/{id}/itens/{item_id}/devolver/ — Devolução
        parcial de item (RF-13 / Ponto 2).
        """
        venda = self.get_object()
        if venda.status != 'FINALIZADA':
            return Response(
                {'status': 'Somente vendas FINALIZADA podem ter itens devolvidos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item = get_object_or_404(ItemVenda, pk=item_id, venda=venda, is_active=True)
        ser = DevolverItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        item = devolver_item(
            item=item,
            quantidade=d['quantidade'],
            motivo=d['motivo'],
            pagamento_id=d['pagamento_id'],
            usuario=request.user,
        )
        return Response(ItemVendaSerializer(item).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
