from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from .models import Fornecedor
from .serializers import FornecedorSerializer


class FornecedorViewSet(viewsets.ModelViewSet):
    serializer_class = FornecedorSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nome_razao_social', 'documento', 'email', 'contato_nome']
    ordering_fields = ['nome_razao_social', 'created_at', 'categoria']
    ordering = ['-created_at']

    def get_queryset(self):
        return Fornecedor.objects.filter(is_active=True)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
