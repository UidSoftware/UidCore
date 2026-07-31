from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import AcionistaFornecedor, Fornecedor
from .serializers import AcionistaFornecedorSerializer, FornecedorSerializer


class FornecedorViewSet(viewsets.ModelViewSet):
    serializer_class = FornecedorSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nome_razao_social', 'documento', 'email', 'contato_nome']
    ordering_fields = ['nome_razao_social', 'created_at', 'categoria']
    ordering = ['-created_at']

    def get_queryset(self):
        return Fornecedor.objects.filter(is_active=True).prefetch_related('acionistas')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get', 'post'], url_path='acionistas')
    def acionistas(self, request, pk=None):
        fornecedor = self.get_object()
        if request.method == 'GET':
            qs = AcionistaFornecedor.objects.filter(fornecedor=fornecedor, is_active=True)
            return Response(AcionistaFornecedorSerializer(qs, many=True).data)
        serializer = AcionistaFornecedorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(fornecedor=fornecedor)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'acionistas/(?P<acid>\d+)')
    def acionista_detalhe(self, request, pk=None, acid=None):
        fornecedor = self.get_object()
        try:
            acionista = AcionistaFornecedor.objects.get(pk=acid, fornecedor=fornecedor, is_active=True)
        except AcionistaFornecedor.DoesNotExist:
            return Response({'detail': 'Acionista não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'DELETE':
            acionista.is_active = False
            acionista.save(update_fields=['is_active', 'updated_at'])
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = AcionistaFornecedorSerializer(acionista, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
