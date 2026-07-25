from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .models import Agenda, Compromisso
from .serializers import AgendaSerializer, CompromissoSerializer


class AgendaViewSet(ModelViewSet):
    queryset = Agenda.objects.filter(is_active=True).order_by('nome')
    serializer_class = AgendaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nome']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompromissoViewSet(ModelViewSet):
    queryset = (
        Compromisso.objects.filter(is_active=True)
        .select_related('agenda', 'cliente')
        .order_by('inicio')
    )
    serializer_class = CompromissoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['agenda', 'status', 'cliente']
    search_fields = ['titulo', 'descricao']
    ordering_fields = ['inicio', 'fim']

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
