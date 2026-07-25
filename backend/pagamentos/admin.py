from django.contrib import admin

from .models import Cobranca, MetodoPagamento, Parcela


@admin.register(MetodoPagamento)
class MetodoPagamentoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo', 'is_active']
    list_filter = ['ativo', 'is_active']


@admin.register(Cobranca)
class CobrancaAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'cliente', 'valor', 'vencimento', 'status', 'is_active']
    list_filter = ['status', 'is_active']
    search_fields = ['descricao']
    date_hierarchy = 'vencimento'


@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
    list_display = ['cobranca', 'numero', 'valor', 'vencimento', 'status']
    list_filter = ['status', 'is_active']
