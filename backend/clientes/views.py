from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import AcionistaCliente, Cliente, HistoricoCliente
from .serializers import AcionistaClienteSerializer, ClienteSerializer, HistoricoClienteSerializer


class ClienteViewSet(viewsets.ModelViewSet):
    serializer_class = ClienteSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nome_razao_social', 'documento', 'email', 'cidade']
    ordering_fields = ['nome_razao_social', 'created_at', 'segmento']
    ordering = ['-created_at']

    def get_queryset(self):
        return Cliente.objects.filter(is_active=True).prefetch_related('historico', 'acionistas')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='historico')
    def adicionar_historico(self, request, pk=None):
        cliente = self.get_object()
        serializer = HistoricoClienteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(cliente=cliente)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'], url_path='acionistas')
    def acionistas(self, request, pk=None):
        cliente = self.get_object()
        if request.method == 'GET':
            qs = AcionistaCliente.objects.filter(cliente=cliente, is_active=True)
            return Response(AcionistaClienteSerializer(qs, many=True).data)
        serializer = AcionistaClienteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(cliente=cliente)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'acionistas/(?P<acid>\d+)')
    def acionista_detalhe(self, request, pk=None, acid=None):
        cliente = self.get_object()
        try:
            acionista = AcionistaCliente.objects.get(pk=acid, cliente=cliente, is_active=True)
        except AcionistaCliente.DoesNotExist:
            return Response({'detail': 'Acionista não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'DELETE':
            acionista.is_active = False
            acionista.save(update_fields=['is_active', 'updated_at'])
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = AcionistaClienteSerializer(acionista, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
