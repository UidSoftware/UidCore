from django.contrib import admin

from common.admin import AuditModelAdmin

from .models import Cobranca, MetodoPagamento, Parcela


@admin.register(MetodoPagamento)
class MetodoPagamentoAdmin(AuditModelAdmin):
    list_display = ['nome', 'is_active']
    list_filter = ['is_active']


@admin.register(Cobranca)
class CobrancaAdmin(AuditModelAdmin):
    list_display = ['descricao', 'cliente', 'valor', 'vencimento', 'status', 'is_active']
    list_filter = ['status', 'is_active']
    search_fields = ['descricao']
    date_hierarchy = 'vencimento'


@admin.register(Parcela)
class ParcelaAdmin(AuditModelAdmin):
    list_display = ['cobranca', 'numero', 'valor', 'vencimento', 'status']
    list_filter = ['status', 'is_active']
