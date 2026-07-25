from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'metodos',   views.MetodoPagamentoViewSet, basename='metodo-pagamento')
router.register(r'cobrancas', views.CobrancaViewSet,        basename='cobranca')
router.register(r'parcelas',  views.ParcelaViewSet,         basename='parcela')

urlpatterns = [
    path('', include(router.urls)),
]
