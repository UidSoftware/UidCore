from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'orcamentos',   views.OrcamentoViewSet,  basename='orcamento')
router.register(r'pedidos',      views.PedidoViewSet,     basename='pedido')
router.register(r'itens-pedido', views.ItemPedidoViewSet, basename='item-pedido')

urlpatterns = [
    path('', include(router.urls)),
]
