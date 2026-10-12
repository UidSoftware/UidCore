from django.contrib import admin
from common.admin import AuditModelAdmin
from .models import Fornecedor


@admin.register(Fornecedor)
class FornecedorAdmin(AuditModelAdmin):
    list_display = ['nome_razao_social', 'tipo_pessoa', 'documento', 'categoria', 'cidade', 'estado', 'is_active']
    list_filter = ['tipo_pessoa', 'categoria', 'estado', 'is_active']
    search_fields = ['nome_razao_social', 'documento', 'email', 'contato_nome']
    ordering = ['-created_at']
