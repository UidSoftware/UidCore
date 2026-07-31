from rest_framework.routers import DefaultRouter

from .views import ProdutoViewSet

router = DefaultRouter()
router.register(r'', ProdutoViewSet, basename='produto')

urlpatterns = router.urls
