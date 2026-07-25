from django.contrib import admin

from .models import AcessoPortalCliente


@admin.register(AcessoPortalCliente)
class AcessoPortalClienteAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'cliente', 'ativo', 'ultimo_acesso', 'criado_em']
    list_filter = ['ativo']
    search_fields = ['usuario__email', 'cliente__nome_razao_social']
