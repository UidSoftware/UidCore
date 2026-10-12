from django.contrib import admin

from common.admin import AuditModelAdmin

from .models import Campanha, Lead


@admin.register(Campanha)
class CampanhaAdmin(AuditModelAdmin):
    list_display = ['nome', 'canal', 'status', 'data_inicio', 'data_fim', 'orcamento', 'is_active']
    list_filter = ['canal', 'status', 'is_active']
    search_fields = ['nome']


@admin.register(Lead)
class LeadAdmin(AuditModelAdmin):
    list_display = ['nome', 'email', 'telefone', 'campanha', 'status', 'cliente_convertido', 'is_active']
    list_filter = ['status', 'is_active']
    search_fields = ['nome', 'email', 'telefone']
