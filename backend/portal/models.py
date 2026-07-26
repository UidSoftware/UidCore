from django.conf import settings
from django.db import models


class AcessoPortalCliente(models.Model):
    usuario       = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.CASCADE, related_name='acesso_portal',
    )
    cliente       = models.ForeignKey(
        'clientes.Cliente', null=True, blank=True,
        on_delete=models.PROTECT, related_name='acessos_portal',
    )
    ativo         = models.BooleanField(default=True)
    ultimo_acesso = models.DateTimeField(null=True, blank=True)
    criado_em     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'portal_acesso_cliente'

    def __str__(self):
        return f'{self.usuario} -> {self.cliente}'
