from django.contrib import admin

from common.admin import AuditModelAdmin

from .models import Compra, ItemCompra


class ItemCompraInline(admin.TabularInline):
    model = ItemCompra
    extra = 0
    readonly_fields = ['movimento_estoque']


@admin.register(Compra)
class CompraAdmin(AuditModelAdmin):
    list_display = ['id', 'fornecedor', 'numero_nota_fiscal', 'data_emissao', 'valor_total', 'status']
    list_filter = ['status', 'forma_pagamento']
    search_fields = ['numero_nota_fiscal', 'fornecedor__nome_razao_social']
    readonly_fields = ['valor_total', 'despesa']
    inlines = [ItemCompraInline]
