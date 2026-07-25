from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'agendas',      views.AgendaViewSet,      basename='agenda')
router.register(r'compromissos', views.CompromissoViewSet, basename='compromisso')

urlpatterns = [
    path('', include(router.urls)),
]
