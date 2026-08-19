from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
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
    queryset = Colaborador.objects.filter(is_active=True).select_related('cargo', 'usuario').order_by('nome')
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

    def perform_create(self, serializer):
        """
        RN (19/08/2026): "criar_usuario" e um campo extra (nao existe no
        model Colaborador nem no serializer) -- mesmo padrao ja usado em
        outros lugares do projeto pra recorrencia/flags que nao fazem
        parte do model, lido direto de self.request.data. So IsAdmin
        pode criar acesso ao sistema, mesmo que ColaboradorViewSet em si
        seja aberto pra qualquer autenticado.

        Fix Manutencao #44 (RN-CRITICA/RF-01): toda validacao relacionada a
        criar_usuario (permissao, email duplicado, senha curta) roda ANTES
        de qualquer persistencia -- nada de Colaborador salvo primeiro e
        validado depois. Colaborador.save() + User.save() ficam dentro do
        MESMO transaction.atomic, entao qualquer excecao (inclusive uma
        IntegrityError de corrida que escape das checagens acima) desfaz
        os dois juntos. Nunca fica Colaborador orfao no banco.
        """
        criar_usuario = str(self.request.data.get('criar_usuario', '')).lower() in ('1', 'true', 'on')

        if not criar_usuario:
            serializer.save()
            return

        if not self.request.user.is_staff:
            raise PermissionDenied('Somente administradores podem criar acesso ao sistema.')

        from accounts.models import User
        from accounts.services import enviar_primeiro_acesso

        email = (
            self.request.data.get('usuario_email')
            or serializer.validated_data.get('email')
            or ''
        ).strip().lower()
        if not email:
            raise ValidationError({'usuario_email': 'Informe um email (do colaborador ou de acesso) para criar o usuario.'})
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({'usuario_email': 'Ja existe um usuario com esse email.'})

        senha = self.request.data.get('usuario_senha') or ''
        if senha and len(senha) < 6:
            raise ValidationError({'usuario_senha': 'A senha deve ter pelo menos 6 caracteres.'})

        with transaction.atomic():
            colaborador = serializer.save()

            usuario = User(email=email, nome_completo=colaborador.nome or email)
            if senha:
                usuario.set_password(senha)
            else:
                usuario.set_unusable_password()
            usuario.save()

            colaborador.usuario = usuario
            colaborador.save(update_fields=['usuario'])

        if not senha:
            try:
                enviar_primeiro_acesso(usuario)
            except Exception:
                # Nao falha a criacao do colaborador so por falha no envio do
                # email -- o admin pode reenviar depois pela tela Usuarios
                # ("Enviar acesso").
                pass


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
