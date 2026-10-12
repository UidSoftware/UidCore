from django.contrib import admin

from common.admin import AuditModelAdmin

from .models import Assinatura, Plano


@admin.register(Plano)
class PlanoAdmin(AuditModelAdmin):
    list_display = ['id', 'nome', 'valor', 'periodicidade', 'categoria', 'ativo', 'is_active']
    list_filter = ['periodicidade', 'ativo']
    search_fields = ['nome']


@admin.register(Assinatura)
class AssinaturaAdmin(AuditModelAdmin):
    list_display = ['id', 'cliente', 'plano', 'valor', 'dia_vencimento', 'status', 'data_inicio', 'data_fim']
    list_filter = ['status', 'plano']
    search_fields = ['cliente__nome_razao_social', 'plano__nome']
    readonly_fields = ['encerrada_em']
