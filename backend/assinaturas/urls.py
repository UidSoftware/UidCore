from rest_framework.routers import DefaultRouter

from .views import AssinaturaViewSet, PlanoViewSet

router = DefaultRouter()
router.register('planos', PlanoViewSet, basename='plano')
router.register('assinaturas', AssinaturaViewSet, basename='assinatura')

urlpatterns = router.urls
