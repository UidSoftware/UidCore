from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'nome_completo', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['email', 'nome_completo']
    ordering = ['-date_joined']
    actions = ['enviar_acesso']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Dados pessoais', {'fields': ('nome_completo', 'telefone')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nome_completo', 'password1', 'password2'),
        }),
    )

    @admin.action(description='Enviar email de primeiro acesso (definir senha)')
    def enviar_acesso(self, request, queryset):
        from .services import enviar_primeiro_acesso

        enviados, falhas = 0, []
        for usuario in queryset.filter(is_active=True):
            try:
                enviar_primeiro_acesso(usuario)
                enviados += 1
            except Exception as e:
                falhas.append(f'{usuario.email}: {e}')

        if enviados:
            self.message_user(request, f'{enviados} email(s) de acesso enviado(s).', messages.SUCCESS)
        for falha in falhas:
            self.message_user(request, f'Falha ao enviar para {falha}', messages.ERROR)
