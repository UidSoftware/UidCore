from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'agendas',               views.AgendaViewSet,             basename='agenda')
router.register(r'compromissos',          views.CompromissoViewSet,        basename='compromisso')
router.register(r'horarios-disponiveis',  views.HorarioDisponivelViewSet,  basename='horario-disponivel')

urlpatterns = [
    path('', include(router.urls)),
]
