"""
URLs públicas (AllowAny) do app agendamento.
Montadas em /api/v1/publico/ via core/urls.py.
"""
from django.urls import path

from .views import AgendaDisponibilidadePublicaView, AgendamentoPublicoView

urlpatterns = [
    path('agenda/<slug:slug>/disponibilidade/', AgendaDisponibilidadePublicaView.as_view()),
    path('agenda/<slug:slug>/agendar/', AgendamentoPublicoView.as_view()),
]
