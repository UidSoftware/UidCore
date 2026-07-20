from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('categorias', views.CategoriaViewSet, basename='categoria')
router.register('contas', views.ContaViewSet, basename='conta')
router.register('aportes', views.AporteViewSet, basename='aporte')
router.register('receitas', views.ReceitaViewSet, basename='receita')
router.register('despesas', views.DespesaViewSet, basename='despesa')
router.register('livro-caixa', views.LivroCaixaViewSet, basename='livro-caixa')

urlpatterns = [
    path('', include(router.urls)),
    path('fluxo-caixa/', views.fluxo_caixa, name='fluxo-caixa'),
    path('dre/', views.dre, name='dre'),
    path('dashboard/', views.dashboard_financeiro, name='dashboard-financeiro'),
]
