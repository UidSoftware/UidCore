from datetime import date, datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from accounts.models import PerfilUsuario
from common.mixins import AuditMixin

from .models import (
    Agenda, Compromisso, HorarioDisponivel,
    OrigemCompromisso, StatusCompromisso,
)
from .serializers import (
    AgendaSerializer, AgendamentoPublicoSerializer,
    CompromissoSerializer, HorarioDisponivelSerializer,
    _validar_dia_semana,
)


def _criar_compromisso_com_validacao_vaga(horario, data_horario, **kwargs):
    """
    Cria um Compromisso validando vagas com SELECT FOR UPDATE (RF-04 / RN-01).
    Deve ser chamado DENTRO de uma transaction.atomic() externa, OU cria
    a sua propria quando nao ha transacao encadeada.
    Retorna a instancia criada.
    Levanta ValidationError se nao houver vaga.
    """
    with transaction.atomic():
        h = HorarioDisponivel.objects.select_for_update().get(pk=horario.pk)
        ocupados = Compromisso.objects.filter(
            horario=h,
            data_horario=data_horario,
            is_active=True,
        ).exclude(status=StatusCompromisso.CANCELADO).count()
        if ocupados >= h.vagas:
            raise ValidationError({'erro': 'Horário sem vagas disponíveis.'})
        compromisso = Compromisso.objects.create(
            horario=h,
            data_horario=data_horario,
            **kwargs,
        )
    return compromisso


class AgendaViewSet(AuditMixin, ModelViewSet):
    serializer_class = AgendaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nome']
    # permission_classes: SEM mudanca (continua IsAuthenticated puro) --
    # restringir quebraria OPERACIONAL/MARKETING, que hoje gerenciam
    # agendas livremente (sem staffOnly no Sidebar). Regra do PROFISSIONAL
    # e so de ESCOPO DE DADOS (get_queryset), nao de permissao de entrada
    # (Manutencao 63, RF-07).

    def get_queryset(self):
        qs = Agenda.objects.filter(is_active=True).order_by('nome')
        u = self.request.user
        if u.perfil == PerfilUsuario.PROFISSIONAL and not u.tem_acesso_total:
            qs = qs.filter(Q(profissional=u) | Q(created_by=u))
        return qs


class HorarioDisponivelViewSet(AuditMixin, ModelViewSet):
    serializer_class = HorarioDisponivelSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['agenda', 'dia_semana', 'publico', 'ativo']
    ordering_fields = ['dia_semana', 'hora_inicio']

    def get_queryset(self):
        return HorarioDisponivel.objects.filter(is_active=True).select_related('agenda')

    @action(detail=True, methods=['get'], url_path='ocupacao')
    def ocupacao(self, request, pk=None):
        """
        GET /api/v1/agendamento/horarios-disponiveis/{id}/ocupacao/?data=YYYY-MM-DD
        Retorna vagas, vagas_ocupadas, vagas_disponiveis e lista de compromissos.
        """
        horario = self.get_object()
        data_str = request.query_params.get('data')
        if not data_str:
            return Response(
                {'erro': 'Parâmetro "data" (YYYY-MM-DD) é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            data = date.fromisoformat(data_str)
        except ValueError:
            return Response(
                {'erro': 'Formato de data inválido. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        compromissos_qs = Compromisso.objects.filter(
            horario=horario,
            data_horario=data,
            is_active=True,
        ).exclude(status=StatusCompromisso.CANCELADO)

        vagas_ocupadas = compromissos_qs.count()
        vagas_disponiveis = max(0, horario.vagas - vagas_ocupadas)

        compromissos_data = [
            {
                'id': c.pk,
                'titulo': c.titulo,
                'nome_contato': c.nome_contato,
                'status': c.status,
            }
            for c in compromissos_qs.order_by('inicio')
        ]

        return Response({
            'vagas': horario.vagas,
            'vagas_ocupadas': vagas_ocupadas,
            'vagas_disponiveis': vagas_disponiveis,
            'compromissos': compromissos_data,
        })


class CompromissoViewSet(AuditMixin, ModelViewSet):
    serializer_class = CompromissoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['agenda', 'status', 'cliente', 'origem']
    search_fields = ['titulo', 'descricao', 'nome_contato']
    ordering_fields = ['inicio', 'fim']
    # permission_classes: idem AgendaViewSet -- sem mudanca (Manutencao 63, RF-08).

    def get_queryset(self):
        qs = (
            Compromisso.objects.filter(is_active=True)
            .select_related('agenda', 'cliente', 'horario')
            .order_by('inicio')
        )
        u = self.request.user
        if u.perfil == PerfilUsuario.PROFISSIONAL and not u.tem_acesso_total:
            qs = qs.filter(Q(created_by=u) | Q(agenda__profissional=u))
        return qs

    def perform_create(self, serializer):
        horario = serializer.validated_data.get('horario')
        data_horario = serializer.validated_data.get('data_horario')
        if horario and data_horario:
            # Validacao de vaga atomica (RF-04 / RN-01)
            with transaction.atomic():
                h = HorarioDisponivel.objects.select_for_update().get(pk=horario.pk)
                ocupados = Compromisso.objects.filter(
                    horario=h,
                    data_horario=data_horario,
                    is_active=True,
                ).exclude(status=StatusCompromisso.CANCELADO).count()
                if ocupados >= h.vagas:
                    raise ValidationError({'erro': 'Horário sem vagas disponíveis.'})
                serializer.save(created_by=self.request.user)
        else:
            serializer.save(created_by=self.request.user)


# ---------------------------------------------------------------------------
# Endpoints PÚBLICOS (AllowAny + Throttle)
# ---------------------------------------------------------------------------

class AgendaDisponibilidadePublicaView(APIView):
    """
    GET /api/v1/publico/agenda/{slug}/disponibilidade/?de=YYYY-MM-DD&ate=YYYY-MM-DD
    Sem autenticação. Retorna slots com vagas (nunca expõe dados pessoais).
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    authentication_classes = []

    def get(self, request, slug):
        agenda = get_object_or_404(
            Agenda,
            slug=slug,
            is_active=True,
            permite_agendamento_publico=True,
        )

        de_str = request.query_params.get('de')
        ate_str = request.query_params.get('ate')

        if not de_str or not ate_str:
            return Response(
                {'erro': 'Parâmetros "de" e "ate" (YYYY-MM-DD) são obrigatórios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            de = date.fromisoformat(de_str)
            ate = date.fromisoformat(ate_str)
        except ValueError:
            return Response(
                {'erro': 'Formato de data inválido. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (ate - de).days > 60:
            return Response(
                {'erro': 'Intervalo máximo de consulta é 60 dias.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if ate < de:
            return Response(
                {'erro': '"ate" deve ser maior ou igual a "de".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        horarios = HorarioDisponivel.objects.filter(
            agenda=agenda,
            publico=True,
            ativo=True,
            is_active=True,
        ).order_by('dia_semana', 'hora_inicio')

        resultado = []
        delta = ate - de
        for i in range(delta.days + 1):
            dia = de + timedelta(days=i)
            dia_semana_num = dia.weekday()  # 0=Seg, 6=Dom
            slots_do_dia = [h for h in horarios if h.dia_semana == dia_semana_num]
            for horario in slots_do_dia:
                ocupados = Compromisso.objects.filter(
                    horario=horario,
                    data_horario=dia,
                    is_active=True,
                ).exclude(status=StatusCompromisso.CANCELADO).count()
                vagas_disponiveis = max(0, horario.vagas - ocupados)
                resultado.append({
                    'horario_id': horario.pk,
                    'data': dia.isoformat(),
                    'dia_semana': dia_semana_num,
                    'hora_inicio': horario.hora_inicio.strftime('%H:%M'),
                    'duracao_minutos': horario.duracao_minutos,
                    'servico': horario.servico,
                    'vagas': horario.vagas,
                    'vagas_ocupadas': ocupados,
                    'vagas_disponiveis': vagas_disponiveis,
                    'lotado': vagas_disponiveis == 0,
                })

        return Response(resultado)


class AgendamentoPublicoView(APIView):
    """
    POST /api/v1/publico/agenda/{slug}/agendar/
    Sem autenticação. Throttle por IP. Cria Compromisso com origem=PUBLICO.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    authentication_classes = []

    def post(self, request, slug):
        # Verifica agenda
        agenda = get_object_or_404(
            Agenda,
            slug=slug,
            is_active=True,
            permite_agendamento_publico=True,
        )

        serializer = AgendamentoPublicoSerializer(
            data=request.data,
            context={'slug': slug, 'request': request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        horario = serializer.validated_data['_horario_obj']
        data_horario = serializer.validated_data['data_horario']
        nome_contato = serializer.validated_data['nome_contato']
        telefone_contato = serializer.validated_data['telefone_contato']
        email_contato = serializer.validated_data.get('email_contato', '')

        hora_inicio = horario.hora_inicio
        inicio_dt = datetime.combine(data_horario, hora_inicio)
        fim_dt = inicio_dt + timedelta(minutes=horario.duracao_minutos)

        try:
            with transaction.atomic():
                h = HorarioDisponivel.objects.select_for_update().get(pk=horario.pk)
                ocupados = Compromisso.objects.filter(
                    horario=h,
                    data_horario=data_horario,
                    is_active=True,
                ).exclude(status=StatusCompromisso.CANCELADO).count()
                if ocupados >= h.vagas:
                    return Response(
                        {'erro': 'Horário sem vagas disponíveis.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                compromisso = Compromisso.objects.create(
                    agenda=agenda,
                    horario=h,
                    data_horario=data_horario,
                    inicio=inicio_dt,
                    fim=fim_dt,
                    origem=OrigemCompromisso.PUBLICO,
                    nome_contato=nome_contato,
                    telefone_contato=telefone_contato,
                    email_contato=email_contato,
                    status=StatusCompromisso.AGENDADO,
                    titulo=f'{h.servico} — {nome_contato}' if h.servico else nome_contato,
                )
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {'id': compromisso.pk, 'mensagem': 'Agendamento confirmado.'},
            status=status.HTTP_201_CREATED,
        )
