from django.contrib import admin
from .models import ConversaoUnidade, EntradaEstoque, Produto

admin.site.register(Produto)
admin.site.register(ConversaoUnidade)
admin.site.register(EntradaEstoque)
