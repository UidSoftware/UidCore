from rest_framework.routers import DefaultRouter
from .views import FornecedorViewSet

router = DefaultRouter()
router.register(r'', FornecedorViewSet, basename='fornecedor')

urlpatterns = router.urls
