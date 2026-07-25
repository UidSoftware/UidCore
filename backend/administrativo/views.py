from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .models import Documento, TipoDocumento
from .serializers import DocumentoSerializer, TipoDocumentoSerializer


class TipoDocumentoViewSet(ModelViewSet):
    queryset = TipoDocumento.objects.filter(is_active=True).order_by('nome')
    serializer_class = TipoDocumentoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nome']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentoViewSet(ModelViewSet):
    queryset = (
        Documento.objects.filter(is_active=True)
        .select_related('tipo', 'cliente')
        .order_by('-created_at')
    )
    serializer_class = DocumentoSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'tipo', 'cliente']
    search_fields = ['titulo', 'descricao']
    ordering_fields = ['created_at', 'validade']

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
