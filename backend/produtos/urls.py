from rest_framework.routers import DefaultRouter

from .views import ComboViewSet, ProdutoViewSet

router = DefaultRouter()
router.register(r'combos', ComboViewSet, basename='combo')
router.register(r'', ProdutoViewSet, basename='produto')

urlpatterns = router.urls
