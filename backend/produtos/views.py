from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch
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
        # CA-03: prefetch já filtrado por is_active — o campo aninhado
        # 'conversoes' do ProdutoSerializer nunca deve expor conversão
        # soft-deletada (ver ProdutoSerializer.get_conversoes).
        return Produto.objects.filter(is_active=True).prefetch_related(
            Prefetch('conversoes', queryset=ConversaoUnidade.objects.filter(is_active=True)),
        )

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

        serializer = ConversaoUnidadeSerializer(data=request.data, context={'produto': produto})
        serializer.is_valid(raise_exception=True)

        # unique_together = ('produto', 'unidade') não distingue is_active
        # — reexcluir e recriar a mesma unidade batia direto no
        # IntegrityError (500). Registro soft-deletado pra essa unidade
        # é reativado com os dados novos em vez de INSERT.
        unidade = serializer.validated_data.get('unidade')
        existente = ConversaoUnidade.objects.filter(produto=produto, unidade=unidade).first()
        if existente is not None:
            if existente.is_active:
                return Response(
                    {'unidade': ['Já existe uma conversão ativa para esta unidade.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            for campo, valor in serializer.validated_data.items():
                setattr(existente, campo, valor)
            existente.is_active = True
            existente.save()
            return Response(
                ConversaoUnidadeSerializer(existente).data, status=status.HTTP_201_CREATED,
            )

        serializer.save(produto=produto)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'conversoes/(?P<conv_id>\d+)')
    def conversao_detalhe(self, request, pk=None, conv_id=None):
        produto = self.get_object()
        try:
            conversao = ConversaoUnidade.objects.get(pk=conv_id, produto=produto, is_active=True)
        except ConversaoUnidade.DoesNotExist:
            return Response({'detail': 'Conversão não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        # RN-06: bloqueia editar/excluir uma conversão usada como elo
        # intermediário por outra (ex.: excluir PT quando CX = "1 CX = 6 PT").
        dependentes = ConversaoUnidade.objects.filter(
            produto=produto, converte_para=conversao.unidade, is_active=True,
        ).exclude(pk=conversao.pk)
        if dependentes.exists():
            return Response({
                'detail': (
                    f'A conversão de "{conversao.unidade}" é usada como referência '
                    f'por outra(s) conversão(ões) e não pode ser editada nem excluída.'
                ),
                'dependentes': list(dependentes.values_list('unidade', flat=True)),
            }, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'DELETE':
            conversao.is_active = False
            conversao.save(update_fields=['is_active', 'updated_at'])
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = ConversaoUnidadeSerializer(
            conversao, data=request.data, partial=True, context={'produto': produto},
        )
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
        try:
            serializer.save(produto=produto, criado_por=request.user)
        except DjangoValidationError as exc:
            # RN-05: unidade sem conversão cadastrada (direta ou em cadeia)
            # — nunca mais soma no estoque com fallback 1:1 silencioso.
            return Response(
                {'unidade': exc.messages if hasattr(exc, 'messages') else [str(exc)]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
