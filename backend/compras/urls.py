from rest_framework.routers import DefaultRouter

from .views import CompraViewSet

router = DefaultRouter()
router.register(r'', CompraViewSet, basename='compra')

urlpatterns = router.urls
