from django.contrib import admin

from common.admin import AuditModelAdmin

from .models import AcessoPortalCliente


@admin.register(AcessoPortalCliente)
class AcessoPortalClienteAdmin(AuditModelAdmin):
    list_display = ['usuario', 'cliente', 'is_active', 'ultimo_acesso', 'created_at']
    list_filter = ['is_active']
    search_fields = ['usuario__email', 'cliente__nome_razao_social']
