from django.contrib import admin

from .models import ItemPedido, Orcamento, Pedido


@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'status', 'valor_total', 'validade', 'is_active']
    list_filter = ['status', 'is_active']
    search_fields = ['numero', 'descricao']


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'status', 'valor_total', 'data_pedido', 'is_active']
    list_filter = ['status', 'is_active']
    search_fields = ['numero']
    date_hierarchy = 'data_pedido'


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ['pedido', 'descricao', 'quantidade', 'valor_unitario', 'valor_total']
    list_filter = ['is_active']
    search_fields = ['descricao']
