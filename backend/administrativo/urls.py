from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'tipos',      views.TipoDocumentoViewSet, basename='tipo-documento')
router.register(r'documentos', views.DocumentoViewSet,     basename='documento')

urlpatterns = [
    path('', include(router.urls)),
]
