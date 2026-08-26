from rest_framework.routers import DefaultRouter

from .views import CampanhaViewSet, LeadViewSet

router = DefaultRouter()
router.register('campanhas', CampanhaViewSet, basename='campanha')
router.register('leads', LeadViewSet, basename='lead')

urlpatterns = router.urls
