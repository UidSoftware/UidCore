from django.contrib import admin
from .models import Cliente, HistoricoCliente


class HistoricoInline(admin.TabularInline):
    model = HistoricoCliente
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nome_razao_social', 'tipo_pessoa', 'documento', 'segmento', 'cidade', 'estado', 'is_active']
    list_filter = ['tipo_pessoa', 'segmento', 'estado', 'is_active']
    search_fields = ['nome_razao_social', 'documento', 'email']
    ordering = ['-created_at']
    inlines = [HistoricoInline]
