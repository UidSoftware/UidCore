from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .models import Cargo, Colaborador, FolhaPagamento, RegistroFerias
from .serializers import (
    CargoSerializer, ColaboradorSerializer,
    FolhaPagamentoSerializer, RegistroFeriasSerializer,
)


class CargoViewSet(ModelViewSet):
    queryset = Cargo.objects.filter(is_active=True).order_by('nome')
    serializer_class = CargoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nome']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ColaboradorViewSet(ModelViewSet):
    queryset = Colaborador.objects.filter(is_active=True).select_related('cargo').order_by('nome')
    serializer_class = ColaboradorSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['cargo', 'regime']
    search_fields = ['nome', 'cpf', 'email']
    ordering_fields = ['nome', 'data_admissao']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class FolhaPagamentoViewSet(ModelViewSet):
    queryset = (
        FolhaPagamento.objects.filter(is_active=True)
        .select_related('colaborador')
        .order_by('-mes_referencia')
    )
    serializer_class = FolhaPagamentoSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['colaborador', 'status']
    ordering_fields = ['mes_referencia', 'salario_liquido']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegistroFeriasViewSet(ModelViewSet):
    queryset = (
        RegistroFerias.objects.filter(is_active=True)
        .select_related('colaborador')
        .order_by('-data_inicio')
    )
    serializer_class = RegistroFeriasSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['colaborador', 'status']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
