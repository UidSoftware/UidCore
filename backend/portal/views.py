from rest_framework.viewsets import ModelViewSet

from .models import AcessoPortalCliente
from .serializers import AcessoPortalClienteSerializer


class AcessoPortalClienteViewSet(ModelViewSet):
    queryset = AcessoPortalCliente.objects.filter(is_active=True).select_related('usuario', 'cliente')
    serializer_class = AcessoPortalClienteSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
