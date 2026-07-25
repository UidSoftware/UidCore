from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'acessos', views.AcessoPortalClienteViewSet, basename='acesso-portal')

urlpatterns = [
    path('', include(router.urls)),
]
