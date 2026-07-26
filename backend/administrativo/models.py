from django.conf import settings
from django.db import models

from common.models import BaseModel


class TipoDocumento(BaseModel):
    nome      = models.CharField(max_length=100, unique=True, null=True, blank=True)
    descricao = models.TextField(blank=True)

    class Meta:
        db_table = 'adm_tipo_documento'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class StatusDocumento(models.TextChoices):
    RASCUNHO  = 'RASCUNHO',  'Rascunho'
    VIGENTE   = 'VIGENTE',   'Vigente'
    EXPIRADO  = 'EXPIRADO',  'Expirado'
    CANCELADO = 'CANCELADO', 'Cancelado'


class Documento(BaseModel):
    titulo     = models.CharField(max_length=255, blank=True)
    tipo       = models.ForeignKey(
        TipoDocumento, null=True, blank=True,
        on_delete=models.PROTECT, related_name='documentos',
    )
    arquivo    = models.FileField(upload_to='docs/', null=True, blank=True)
    cliente    = models.ForeignKey(
        'clientes.Cliente', null=True, blank=True,
        on_delete=models.PROTECT, related_name='documentos',
    )
    descricao  = models.TextField(blank=True)
    status     = models.CharField(
        max_length=10, choices=StatusDocumento.choices, default='RASCUNHO',
    )
    validade   = models.DateField(null=True, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'adm_documento'
        ordering = ['-created_at']

    def __str__(self):
        return self.titulo
