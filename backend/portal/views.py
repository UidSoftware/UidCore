from rest_framework.viewsets import ModelViewSet

from common.mixins import AuditMixin

from .models import AcessoPortalCliente
from .serializers import AcessoPortalClienteSerializer


class AcessoPortalClienteViewSet(AuditMixin, ModelViewSet):
    queryset = AcessoPortalCliente.objects.filter(is_active=True).select_related('usuario', 'cliente')
    serializer_class = AcessoPortalClienteSerializer
