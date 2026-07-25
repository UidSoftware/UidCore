from django.contrib import admin

from .models import Documento, TipoDocumento


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'is_active']
    search_fields = ['nome']


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'tipo', 'cliente', 'status', 'validade', 'is_active']
    list_filter = ['status', 'tipo', 'is_active']
    search_fields = ['titulo']
