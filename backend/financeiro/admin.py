from django.contrib import admin

from .models import Aporte, Categoria, Conta, Despesa, LivroCaixa, Receita


@admin.register(Conta)
class ContaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'banco', 'saldo_inicial', 'is_active']
    list_filter = ['tipo', 'is_active']
    search_fields = ['nome', 'banco']


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'is_active']
    list_filter = ['tipo', 'is_active']
    search_fields = ['nome']


@admin.register(Aporte)
class AporteAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'tipo', 'valor', 'conta', 'data', 'is_active']
    list_filter = ['tipo', 'conta', 'is_active']
    search_fields = ['descricao', 'responsavel']
    date_hierarchy = 'data'


@admin.register(Receita)
class ReceitaAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'tipo', 'valor_liquido', 'status', 'vencimento', 'conta']
    list_filter = ['tipo', 'status', 'conta', 'is_active']
    search_fields = ['descricao']
    date_hierarchy = 'vencimento'


@admin.register(Despesa)
class DespesaAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'tipo', 'valor_liquido', 'status', 'vencimento', 'conta', 'estornado']
    list_filter = ['tipo', 'status', 'conta', 'estornado', 'is_active']
    search_fields = ['descricao', 'fornecedor']
    date_hierarchy = 'vencimento'


@admin.register(LivroCaixa)
class LivroCaixaAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'tipo', 'origem', 'valor', 'data', 'conta', 'saldo_atual', 'estornado']
    list_filter = ['tipo', 'origem', 'conta', 'estornado']
    search_fields = ['descricao']
    date_hierarchy = 'data'
    readonly_fields = ['saldo_anterior', 'saldo_atual', 'criado_em']
from .models import ConciliacaoExtrato, ItemConciliacao, PadraoSeguroConciliacao


@admin.register(ConciliacaoExtrato)
class ConciliacaoExtratoAdmin(admin.ModelAdmin):
    list_display = ['conta', 'periodo', 'status', 'total_banco', 'total_sistema', 'divergencias', 'processado_em']
    list_filter = ['status', 'conta']
    date_hierarchy = 'periodo'
    readonly_fields = ['processado_em', 'total_banco', 'total_sistema', 'divergencias']


@admin.register(ItemConciliacao)
class ItemConciliacaoAdmin(admin.ModelAdmin):
    list_display = ['conciliacao', 'data_banco', 'descricao_banco', 'valor', 'tipo', 'status', 'confirmado']
    list_filter = ['status', 'tipo', 'confirmado']
    search_fields = ['descricao_banco']


@admin.register(PadraoSeguroConciliacao)
class PadraoSeguroConciliacaoAdmin(admin.ModelAdmin):
    list_display = ['descricao_padrao', 'tipo', 'natureza', 'ativo', 'criado_em']
    list_filter = ['tipo', 'natureza', 'ativo']
    search_fields = ['descricao_padrao']
