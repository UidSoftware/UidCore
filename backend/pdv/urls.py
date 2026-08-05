from rest_framework.routers import DefaultRouter

from .views import SessaoCaixaViewSet, VendaViewSet

router = DefaultRouter()
router.register('sessoes', SessaoCaixaViewSet, basename='sessao')
router.register('vendas', VendaViewSet, basename='venda')

urlpatterns = router.urls
