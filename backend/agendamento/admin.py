from django.contrib import admin

from .models import Agenda, Compromisso


@admin.register(Agenda)
class AgendaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cor', 'ativo', 'is_active']
    list_filter = ['ativo', 'is_active']
    search_fields = ['nome']


@admin.register(Compromisso)
class CompromissoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'agenda', 'cliente', 'inicio', 'fim', 'status']
    list_filter = ['status', 'agenda', 'is_active']
    search_fields = ['titulo']
    date_hierarchy = 'inicio'
