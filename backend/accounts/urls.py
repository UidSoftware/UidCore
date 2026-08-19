from django.urls import path
from .views import (
    AlterarSenhaView, DefinirSenhaView, RegisterView, SolicitarAcessoView, UserProfileView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', UserProfileView.as_view(), name='user_profile'),
    path('alterar-senha/', AlterarSenhaView.as_view(), name='alterar_senha'),
    path('solicitar-acesso/', SolicitarAcessoView.as_view(), name='solicitar_acesso'),
    path('definir-senha/', DefinirSenhaView.as_view(), name='definir_senha'),
]
