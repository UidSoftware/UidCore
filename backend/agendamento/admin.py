from django.contrib import admin

from common.admin import AuditModelAdmin

from .models import Agenda, Compromisso


@admin.register(Agenda)
class AgendaAdmin(AuditModelAdmin):
    list_display = ['nome', 'cor', 'is_active']
    list_filter = ['is_active']
    search_fields = ['nome']


@admin.register(Compromisso)
class CompromissoAdmin(AuditModelAdmin):
    list_display = ['titulo', 'agenda', 'cliente', 'inicio', 'fim', 'status']
    list_filter = ['status', 'agenda', 'is_active']
    search_fields = ['titulo']
    date_hierarchy = 'inicio'
