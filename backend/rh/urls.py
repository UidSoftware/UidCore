from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'cargos',        views.CargoViewSet,          basename='cargo')
router.register(r'colaboradores', views.ColaboradorViewSet,     basename='colaborador')
router.register(r'folhas',        views.FolhaPagamentoViewSet,  basename='folha-pagamento')
router.register(r'ferias',        views.RegistroFeriasViewSet,  basename='registro-ferias')

urlpatterns = [
    path('', include(router.urls)),
]
