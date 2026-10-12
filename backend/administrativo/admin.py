from django.contrib import admin

from common.admin import AuditModelAdmin

from .models import Documento, TipoDocumento


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(AuditModelAdmin):
    list_display = ['nome', 'is_active']
    search_fields = ['nome']


@admin.register(Documento)
class DocumentoAdmin(AuditModelAdmin):
    list_display = ['titulo', 'tipo', 'cliente', 'status', 'validade', 'is_active']
    list_filter = ['status', 'tipo', 'is_active']
    search_fields = ['titulo']
