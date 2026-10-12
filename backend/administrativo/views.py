from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import AuditMixin

from .models import Documento, TipoDocumento
from .serializers import DocumentoSerializer, TipoDocumentoSerializer


class TipoDocumentoViewSet(AuditMixin, ModelViewSet):
    queryset = TipoDocumento.objects.filter(is_active=True).order_by('nome')
    serializer_class = TipoDocumentoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nome']


class DocumentoViewSet(AuditMixin, ModelViewSet):
    queryset = (
        Documento.objects.filter(is_active=True)
        .select_related('tipo', 'cliente')
        .order_by('-created_at')
    )
    serializer_class = DocumentoSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'tipo', 'cliente']
    search_fields = ['titulo', 'descricao']
    ordering_fields = ['created_at', 'validade']
