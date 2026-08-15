from django.contrib import admin

from .models import Cargo, Colaborador, FolhaPagamento, RegistroFerias


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'salario_base', 'is_active']
    search_fields = ['nome']


@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cpf', 'cargo', 'regime', 'data_admissao', 'is_active']
    list_filter = ['regime', 'cargo', 'is_active']
    search_fields = ['nome', 'cpf', 'email']


@admin.register(FolhaPagamento)
class FolhaPagamentoAdmin(admin.ModelAdmin):
    list_display = ['colaborador', 'mes_referencia', 'salario_bruto', 'salario_liquido', 'status']
    list_filter = ['status', 'is_active']


@admin.register(RegistroFerias)
class RegistroFeriasAdmin(admin.ModelAdmin):
    list_display = ['colaborador', 'data_inicio', 'data_fim', 'dias', 'status']
    list_filter = ['status', 'is_active']
