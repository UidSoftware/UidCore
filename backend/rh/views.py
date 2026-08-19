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

    def _validar_criar_usuario(self, email_fallback):
        """
        RF-01 (Manutencao #45): validacao de "criar_usuario" extraida de
        perform_create pra ser reutilizada por perform_update tambem. So
        IsAdmin pode criar acesso ao sistema, mesmo que ColaboradorViewSet
        em si seja aberto pra qualquer autenticado. Roda ANTES de qualquer
        persistencia -- levanta PermissionDenied/ValidationError sem
        salvar nada, e quem chama decide o que fazer com o retorno dentro
        do proprio transaction.atomic().

        Retorna (email, senha) ja normalizados: email em minusculo/sem
        espacos (usuario_email do request tem prioridade sobre
        email_fallback), senha como veio (sem espacos nas pontas) ou ''.
        """
        if not self.request.user.is_staff:
            raise PermissionDenied('Somente administradores podem criar acesso ao sistema.')

        from accounts.models import User

        email = (
            self.request.data.get('usuario_email')
            or email_fallback
            or ''
        ).strip().lower()
        if not email:
            raise ValidationError({'usuario_email': 'Informe um email (do colaborador ou de acesso) para criar o usuario.'})
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({'usuario_email': 'Ja existe um usuario com esse email.'})

        senha = (self.request.data.get('usuario_senha') or '').strip()
        if senha and len(senha) < 6:
            raise ValidationError({'usuario_senha': 'A senha deve ter pelo menos 6 caracteres.'})

        return email, senha

    def _criar_usuario_para_colaborador(self, colaborador, email, senha):
        """
        RF-02 (Manutencao #45): criacao efetiva do User + vinculo ao
        Colaborador, extraida de perform_create pra ser reutilizada por
        perform_update. Quem chama e responsavel por rodar isso dentro de
        um transaction.atomic() junto com o serializer.save() do
        Colaborador -- tudo-ou-nada (RN-02).
        """
        from accounts.models import User
        from accounts.services import enviar_primeiro_acesso

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
                # Nao falha a criacao/edicao do colaborador so por falha no
                # envio do email -- o admin pode reenviar depois pela tela
                # Usuarios ("Enviar acesso").
                pass

    def perform_create(self, serializer):
        """
        RN (19/08/2026): "criar_usuario" e um campo extra (nao existe no
        model Colaborador nem no serializer) -- mesmo padrao ja usado em
        outros lugares do projeto pra recorrencia/flags que nao fazem
        parte do model, lido direto de self.request.data.

        Fix Manutencao #44 (RN-CRITICA/RF-01): toda validacao relacionada a
        criar_usuario (permissao, email duplicado, senha curta) roda ANTES
        de qualquer persistencia -- nada de Colaborador salvo primeiro e
        validado depois. Colaborador.save() + User.save() ficam dentro do
        MESMO transaction.atomic, entao qualquer excecao (inclusive uma
        IntegrityError de corrida que escape das checagens acima) desfaz
        os dois juntos. Nunca fica Colaborador orfao no banco.

        Refatorado na Manutencao #45 (RF-03) pra reusar
        _validar_criar_usuario/_criar_usuario_para_colaborador com
        perform_update -- mesmo comportamento observavel de antes.
        """
        criar_usuario = str(self.request.data.get('criar_usuario', '')).lower() in ('1', 'true', 'on')

        if not criar_usuario:
            serializer.save()
            return

        email_fallback = serializer.validated_data.get('email') or ''
        email, senha = self._validar_criar_usuario(email_fallback)

        with transaction.atomic():
            colaborador = serializer.save()
            self._criar_usuario_para_colaborador(colaborador, email, senha)

    def perform_update(self, serializer):
        """
        RF-04 (Manutencao #45): permite criar acesso tambem ao EDITAR um
        colaborador que ainda nao tem acesso (usuario_id vazio) -- ate
        aqui um PATCH com criar_usuario=true era ignorado silenciosamente
        pelo ModelViewSet.perform_update padrao (campo nao existe no
        serializer).

        RN-01/RN-02: guarda contra dar acesso duas vezes roda depois do
        serializer.save() mas dentro do MESMO transaction.atomic() --
        se levantar ValidationError, o rollback desfaz tambem a
        atualizacao do Colaborador feita por serializer.save() logo
        acima, entao nada fica salvo pela metade.

        RN-04: fallback de email diferente do perform_create -- aqui o
        colaborador ja existe, entao cai por ultimo no email ja
        persistido nele (serializer.instance.email) se nem o request nem
        o payload validado trouxerem um novo.
        """
        with transaction.atomic():
            colaborador = serializer.save()

            criar_usuario = str(self.request.data.get('criar_usuario', '')).lower() in ('1', 'true', 'on')
            if not criar_usuario:
                return

            if serializer.instance.usuario_id:
                raise ValidationError('Colaborador já possui acesso ao sistema')

            email_fallback = (
                serializer.validated_data.get('email')
                or serializer.instance.email
            )
            email, senha = self._validar_criar_usuario(email_fallback)
            self._criar_usuario_para_colaborador(colaborador, email, senha)


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
