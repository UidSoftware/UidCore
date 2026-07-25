from rest_framework.viewsets import ModelViewSet

from .models import AcessoPortalCliente
from .serializers import AcessoPortalClienteSerializer


class AcessoPortalClienteViewSet(ModelViewSet):
    queryset = AcessoPortalCliente.objects.filter(ativo=True).select_related('usuario', 'cliente')
    serializer_class = AcessoPortalClienteSerializer

    def perform_destroy(self, instance):
        instance.ativo = False
        instance.save(update_fields=['ativo'])
