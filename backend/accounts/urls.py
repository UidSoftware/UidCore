from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    AlterarSenhaView, DefinirSenhaView, RegisterView, SolicitarAcessoView, UserProfileView, UserViewSet,
)

router = DefaultRouter()
router.register('usuarios', UserViewSet, basename='usuario')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', UserProfileView.as_view(), name='user_profile'),
    path('alterar-senha/', AlterarSenhaView.as_view(), name='alterar_senha'),
    path('solicitar-acesso/', SolicitarAcessoView.as_view(), name='solicitar_acesso'),
    path('definir-senha/', DefinirSenhaView.as_view(), name='definir_senha'),
    path('', include(router.urls)),
]
