from django.contrib import admin

from common.admin import AuditModelAdmin

from .models import Combo, ConversaoUnidade, MovimentoEstoque, Produto

admin.site.register(Produto, AuditModelAdmin)
admin.site.register(ConversaoUnidade, AuditModelAdmin)
admin.site.register(MovimentoEstoque, AuditModelAdmin)
admin.site.register(Combo, AuditModelAdmin)
