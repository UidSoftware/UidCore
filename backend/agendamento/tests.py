"""Testes do app agendamento.

Manutencao #7: RF-AG01 a RF-AG03 e RN-AG01 a RN-AG03.
Manutencao #63: escopo PROFISSIONAL.
Manutencao #65 [NUCLEO 4/5]: HorarioDisponivel, vagas, concorrencia, publico.
"""
import threading
from datetime import date

from django.core.cache import cache
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import User

from .models import Agenda, Compromisso, HorarioDisponivel


def _make_user(email='admin@teste.com'):
    return User.objects.create_user(email=email, password='senha123', nome_completo='Admin Teste')


def _make_agenda(nome='Agenda Principal'):
    return Agenda.objects.create(nome=nome)


class AgendaModelTest(TestCase):
    def test_cor_default_rn_ag02(self):
        agenda = _make_agenda()
        self.assertEqual(agenda.cor, '#3B82F6')

    def test_soft_delete_rn_ag03(self):
        agenda = _make_agenda()
        agenda.is_active = False
        agenda.save()
        self.assertTrue(Agenda.objects.filter(pk=agenda.pk).exists())


class CompromissoModelTest(TestCase):
    def setUp(self):
        self.agenda = _make_agenda()

    def test_criar_compromisso_rf_ag02(self):
        compromisso = Compromisso.objects.create(
            agenda=self.agenda, titulo='Reuniao', inicio='2026-07-20T10:00:00Z', fim='2026-07-20T11:00:00Z',
        )
        self.assertEqual(compromisso.status, 'AGENDADO')

    def test_soft_delete_rn_ag03(self):
        compromisso = Compromisso.objects.create(
            agenda=self.agenda, titulo='Reuniao', inicio='2026-07-20T10:00:00Z', fim='2026-07-20T11:00:00Z',
        )
        compromisso.is_active = False
        compromisso.save()
        self.assertTrue(Compromisso.objects.filter(pk=compromisso.pk).exists())


class CompromissoAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.agenda = _make_agenda()

    def test_criar_compromisso_via_api_rf_ag02(self):
        resp = self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': self.agenda.id, 'titulo': 'Consulta', 'inicio': '2026-07-20T10:00:00Z',
            'fim': '2026-07-20T11:00:00Z',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_fim_antes_do_inicio_invalido_rn_ag01(self):
        resp = self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': self.agenda.id, 'titulo': 'Consulta invalida', 'inicio': '2026-07-20T11:00:00Z',
            'fim': '2026-07-20T10:00:00Z',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fim', resp.data)

    def test_destroy_faz_soft_delete_rn_ag03(self):
        compromisso = Compromisso.objects.create(
            agenda=self.agenda, titulo='Del', inicio='2026-07-20T10:00:00Z', fim='2026-07-20T11:00:00Z',
        )
        resp = self.client.delete(f'/api/v1/agendamento/compromissos/{compromisso.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        compromisso.refresh_from_db()
        self.assertFalse(compromisso.is_active)

    def test_listar_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/agendamento/compromissos/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class AgendaAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)

    def test_crud_agendas_rf_ag01(self):
        resp = self.client.post('/api/v1/agendamento/agendas/', {
            'nome': 'Agenda Secundaria', 'cor': '#FF0000',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        agenda_id = resp.data['id']

        resp = self.client.delete(f'/api/v1/agendamento/agendas/{agenda_id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        # Manutencao 62: manager padrao (objects) filtra deleted_at — usar
        # all_objects pra confirmar soft delete (registro continua no banco).
        agenda = Agenda.all_objects.get(pk=agenda_id)
        self.assertFalse(agenda.is_active)
        self.assertIsNotNone(agenda.deleted_at)


class AuditoriaManutencao62APITest(APITestCase):
    """Manutencao 62 — ciclo completo created_by/updated_by/deleted_by/deleted_at."""

    def test_ciclo_completo_auditoria_agenda(self):
        user_a = _make_user(email='a62@teste.com')
        user_b = _make_user(email='b62@teste.com')
        user_c = _make_user(email='c62@teste.com')

        self.client.force_authenticate(user_a)
        resp = self.client.post('/api/v1/agendamento/agendas/', {'nome': 'Agenda Auditoria'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        agenda_id = resp.data['id']
        agenda = Agenda.objects.get(pk=agenda_id)
        self.assertEqual(agenda.created_by, user_a)

        self.client.force_authenticate(user_b)
        resp = self.client.patch(f'/api/v1/agendamento/agendas/{agenda_id}/', {'cor': '#00FF00'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        agenda.refresh_from_db()
        self.assertEqual(agenda.updated_by, user_b)
        self.assertEqual(agenda.created_by, user_a)

        self.client.force_authenticate(user_c)
        resp = self.client.delete(f'/api/v1/agendamento/agendas/{agenda_id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        agenda = Agenda.all_objects.get(pk=agenda_id)
        self.assertEqual(agenda.deleted_by, user_c)
        self.assertIsNotNone(agenda.deleted_at)
        self.assertFalse(Agenda.objects.filter(pk=agenda_id).exists())


# --- Manutencao 63 [NUCLEO 2/5] (RF-05/RF-07/RF-08) — escopo PROFISSIONAL ---
# Cobre CA-05, CA-10, CA-11 (parte agendamento) da Especificacao_Hotfix.md.

def _make_profissional(email):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Profissional Teste',
        perfil='PROFISSIONAL', is_staff=False,
    )


def _make_operacional_agenda(email='operacional-ag@teste.com'):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Operacional Teste', is_staff=False,
    )


class CompromissoEscopoProfissionalAPITest(APITestCase):
    def setUp(self):
        self.profissional_a = _make_profissional('prof-a@teste.com')
        self.profissional_b = _make_profissional('prof-b@teste.com')
        self.recepcionista = _make_operacional_agenda()
        self.agenda_geral = _make_agenda('Agenda Geral')
        self.agenda_do_a = Agenda.objects.create(nome='Agenda do A', profissional=self.profissional_a)

    def test_profissional_ve_apenas_proprio_compromisso_criado_por_ele_ca05(self):
        self.client.force_authenticate(self.profissional_a)
        resp = self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': self.agenda_geral.id, 'titulo': 'Consulta A',
            'inicio': '2026-07-20T10:00:00Z', 'fim': '2026-07-20T11:00:00Z',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        resp = self.client.get('/api/v1/agendamento/compromissos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)

    def test_profissional_b_nao_ve_compromisso_de_outro_ca05(self):
        self.client.force_authenticate(self.profissional_a)
        self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': self.agenda_geral.id, 'titulo': 'Consulta A',
            'inicio': '2026-07-20T10:00:00Z', 'fim': '2026-07-20T11:00:00Z',
        }, format='json')

        self.client.force_authenticate(self.profissional_b)
        resp = self.client.get('/api/v1/agendamento/compromissos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 0)

    def test_profissional_ve_compromisso_criado_por_outro_na_sua_agenda_vinculada_ca05(self):
        # Recepcionista (OPERACIONAL) cria compromisso na agenda do profissional A
        self.client.force_authenticate(self.recepcionista)
        resp = self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': self.agenda_do_a.id, 'titulo': 'Consulta agendada pela recepcao',
            'inicio': '2026-07-20T10:00:00Z', 'fim': '2026-07-20T11:00:00Z',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        self.client.force_authenticate(self.profissional_a)
        resp = self.client.get('/api/v1/agendamento/compromissos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)

    def test_admin_ve_todos_sem_filtro_ca10(self):
        self.client.force_authenticate(self.profissional_a)
        self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': self.agenda_geral.id, 'titulo': 'Consulta A',
            'inicio': '2026-07-20T10:00:00Z', 'fim': '2026-07-20T11:00:00Z',
        }, format='json')
        self.client.force_authenticate(self.profissional_b)
        self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': self.agenda_geral.id, 'titulo': 'Consulta B',
            'inicio': '2026-07-21T10:00:00Z', 'fim': '2026-07-21T11:00:00Z',
        }, format='json')

        admin = _make_user(email='admin-ag-m63@teste.com')
        self.client.force_authenticate(admin)
        resp = self.client.get('/api/v1/agendamento/compromissos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 2)

    def test_profissional_vinculado_via_api_real_ca05(self):
        """CA-05 via API real (nao ORM) -- cobre o gap em que
        AgendaSerializer descartava 'profissional' silenciosamente no
        POST/PATCH (Manutencao 63, correcao pos-Sentinel): cria a Agenda
        pela API com profissional=<id>, confirma profissional_id gravado
        no banco e confirma que o escopo de Compromisso via
        agenda__profissional funciona de ponta a ponta pela API."""
        self.client.force_authenticate(self.recepcionista)
        resp = self.client.post('/api/v1/agendamento/agendas/', {
            'nome': 'Agenda do A via API', 'profissional': self.profissional_a.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        agenda_id = resp.data['id']
        self.assertEqual(resp.data['profissional'], self.profissional_a.id)

        agenda = Agenda.objects.get(pk=agenda_id)
        self.assertEqual(agenda.profissional_id, self.profissional_a.id)

        resp = self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': agenda_id, 'titulo': 'Consulta via agenda criada por API',
            'inicio': '2026-07-20T10:00:00Z', 'fim': '2026-07-20T11:00:00Z',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        self.client.force_authenticate(self.profissional_a)
        resp = self.client.get('/api/v1/agendamento/compromissos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)

        self.client.force_authenticate(self.profissional_b)
        resp = self.client.get('/api/v1/agendamento/compromissos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 0)

    def test_operacional_sem_filtro_de_escopo_ca11(self):
        """RN-07/CA-11 — regra de escopo e so para PROFISSIONAL puro;
        OPERACIONAL continua vendo tudo sem filtro, sem regressao."""
        self.client.force_authenticate(self.profissional_a)
        self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': self.agenda_geral.id, 'titulo': 'Consulta A',
            'inicio': '2026-07-20T10:00:00Z', 'fim': '2026-07-20T11:00:00Z',
        }, format='json')

        self.client.force_authenticate(self.recepcionista)
        resp = self.client.get('/api/v1/agendamento/compromissos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)


class AgendaEscopoProfissionalAPITest(APITestCase):
    def setUp(self):
        self.profissional_a = _make_profissional('prof-agenda-a@teste.com')
        self.profissional_b = _make_profissional('prof-agenda-b@teste.com')
        self.agenda_sem_dono = _make_agenda('Agenda Sem Dono')
        self.agenda_do_a = Agenda.objects.create(nome='Agenda do A', profissional=self.profissional_a)

    def test_profissional_ve_so_a_propria_agenda_vinculada_rf07(self):
        self.client.force_authenticate(self.profissional_a)
        resp = self.client.get('/api/v1/agendamento/agendas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        nomes = [item['nome'] for item in resp.data['results']]
        self.assertIn('Agenda do A', nomes)
        self.assertNotIn('Agenda Sem Dono', nomes)

    def test_profissional_b_nao_ve_agenda_do_a_rf07(self):
        self.client.force_authenticate(self.profissional_b)
        resp = self.client.get('/api/v1/agendamento/agendas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        nomes = [item['nome'] for item in resp.data['results']]
        self.assertNotIn('Agenda do A', nomes)


# ===========================================================================
# Manutencao 65 [NUCLEO 4/5] — HorarioDisponivel, vagas, publico, concorrencia
# ===========================================================================

def _make_agenda_slug(nome='Agenda Publica', slug='agenda-publica', publica=True):
    return Agenda.objects.create(
        nome=nome,
        slug=slug,
        permite_agendamento_publico=publica,
    )


def _make_horario(agenda, dia_semana=0, hora='09:00', duracao=30, vagas=2, publico=True, ativo=True):
    return HorarioDisponivel.objects.create(
        agenda=agenda,
        dia_semana=dia_semana,  # 0 = Segunda
        hora_inicio=hora,
        duracao_minutos=duracao,
        vagas=vagas,
        servico='Consulta',
        publico=publico,
        ativo=ativo,
    )


class HorarioDisponivelAPITest(APITestCase):
    """CA-01: CRUD de HorarioDisponivel autenticado."""

    def setUp(self):
        self.user = _make_user('horario@teste.com')
        self.client.force_authenticate(self.user)
        self.agenda = _make_agenda_slug('Agenda Horarios', 'agenda-horarios')

    def test_criar_horario_ca01(self):
        resp = self.client.post('/api/v1/agendamento/horarios-disponiveis/', {
            'agenda': self.agenda.id,
            'dia_semana': 1,
            'hora_inicio': '10:00',
            'duracao_minutos': 45,
            'vagas': 3,
            'servico': 'Avaliacao',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['vagas'], 3)

    def test_listar_horario_ca01(self):
        _make_horario(self.agenda)
        resp = self.client.get('/api/v1/agendamento/horarios-disponiveis/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data['results']), 1)

    def test_filtro_por_agenda_ca01(self):
        outra = _make_agenda_slug('Outra Agenda', 'outra-agenda')
        _make_horario(self.agenda)
        _make_horario(outra)
        resp = self.client.get(f'/api/v1/agendamento/horarios-disponiveis/?agenda={self.agenda.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for item in resp.data['results']:
            self.assertEqual(item['agenda'], self.agenda.id)

    def test_duracao_invalida_retorna_400(self):
        resp = self.client.post('/api/v1/agendamento/horarios-disponiveis/', {
            'agenda': self.agenda.id,
            'dia_semana': 0,
            'hora_inicio': '08:00',
            'duracao_minutos': 3,  # < 5
            'vagas': 1,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_soft_delete_horario_ca11(self):
        """CA-11: soft delete nao afeta compromissos vinculados."""
        horario = _make_horario(self.agenda)
        comp = Compromisso.objects.create(
            agenda=self.agenda,
            horario=horario,
            data_horario=date(2026, 10, 19),
            titulo='Teste',
            inicio='2026-10-19T09:00:00Z',
            fim='2026-10-19T09:30:00Z',
        )
        resp = self.client.delete(f'/api/v1/agendamento/horarios-disponiveis/{horario.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        horario = HorarioDisponivel.all_objects.get(pk=horario.id)
        self.assertFalse(horario.is_active)
        # Compromisso nao foi afetado
        comp.refresh_from_db()
        self.assertTrue(comp.is_active)

    def test_ocupacao_action_ca14(self):
        """CA-14: action ocupacao retorna vagas corretas para uma data."""
        horario = _make_horario(self.agenda, dia_semana=0, vagas=3)  # 0=segunda
        data_segunda = date(2026, 10, 19)  # segunda-feira
        Compromisso.objects.create(
            agenda=self.agenda, horario=horario, data_horario=data_segunda,
            inicio='2026-10-19T09:00:00Z', fim='2026-10-19T09:30:00Z',
        )
        resp = self.client.get(
            f'/api/v1/agendamento/horarios-disponiveis/{horario.id}/ocupacao/?data=2026-10-19',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['vagas'], 3)
        self.assertEqual(resp.data['vagas_ocupadas'], 1)
        self.assertEqual(resp.data['vagas_disponiveis'], 2)


class VagaValidacaoAPITest(APITestCase):
    """CA-02: validacao sequencial de vagas (sem concorrencia)."""

    def setUp(self):
        self.user = _make_user('vagas@teste.com')
        self.client.force_authenticate(self.user)
        self.agenda = _make_agenda_slug('Agenda Vagas', 'agenda-vagas')
        self.horario = _make_horario(self.agenda, dia_semana=0, vagas=2)  # segunda
        self.data_segunda = '2026-10-19'  # segunda-feira

    def _criar_compromisso(self, titulo='Consulta'):
        return self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': self.agenda.id,
            'titulo': titulo,
            'horario': self.horario.id,
            'data_horario': self.data_segunda,
            'inicio': f'{self.data_segunda}T09:00:00Z',
            'fim': f'{self.data_segunda}T09:30:00Z',
        }, format='json')

    def test_primeiro_e_segundo_criados_ca02(self):
        resp1 = self._criar_compromisso('C1')
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        resp2 = self._criar_compromisso('C2')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)

    def test_terceiro_retorna_400_ca02(self):
        self._criar_compromisso('C1')
        self._criar_compromisso('C2')
        resp3 = self._criar_compromisso('C3')
        self.assertEqual(resp3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('erro', resp3.data)

    def test_cancelado_nao_conta_como_vaga_ca02(self):
        """Compromisso cancelado nao ocupa vaga."""
        resp1 = self._criar_compromisso('C1')
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        comp_id = resp1.data['id']
        # Cancelar
        self.client.patch(f'/api/v1/agendamento/compromissos/{comp_id}/', {
            'status': 'CANCELADO',
        }, format='json')
        # Agora pode criar 2 novos
        resp2 = self._criar_compromisso('C2')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        resp3 = self._criar_compromisso('C3')
        self.assertEqual(resp3.status_code, status.HTTP_201_CREATED)

    def test_compromisso_sem_horario_retrocompativel_ca09(self):
        """CA-09: compromisso avulso sem horario continua funcionando."""
        resp = self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': self.agenda.id,
            'titulo': 'Avulso sem horario',
            'inicio': '2026-10-20T14:00:00Z',
            'fim': '2026-10-20T15:00:00Z',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class AgendaSlugAPITest(APITestCase):
    """Testes de slug em Agenda (RF-09 / RN-03)."""

    def setUp(self):
        self.user = _make_user('slug@teste.com')
        self.client.force_authenticate(self.user)

    def test_slug_gerado_automaticamente(self):
        resp = self.client.post('/api/v1/agendamento/agendas/', {
            'nome': 'Fisioterapia Total',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['slug'], 'fisioterapia-total')

    def test_slug_unico_sufixo_auto(self):
        self.client.post('/api/v1/agendamento/agendas/', {'nome': 'Pilates'}, format='json')
        resp2 = self.client.post('/api/v1/agendamento/agendas/', {'nome': 'Pilates'}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(resp2.data['slug'], 'pilates')
        self.assertIn('pilates', resp2.data['slug'])

    def test_slug_duplicado_explicito_retorna_400(self):
        self.client.post('/api/v1/agendamento/agendas/', {
            'nome': 'Agenda X', 'slug': 'agenda-x',
        }, format='json')
        resp2 = self.client.post('/api/v1/agendamento/agendas/', {
            'nome': 'Outra', 'slug': 'agenda-x',
        }, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)


class DisponibilidadePublicaTest(APITestCase):
    """CA-04 / CA-07: endpoint publico de disponibilidade."""

    def setUp(self):
        # Sem autenticacao
        self.agenda = _make_agenda_slug('Agenda Publica OK', 'agenda-pub-ok', publica=True)
        self.agenda_privada = _make_agenda_slug('Agenda Privada', 'agenda-privada', publica=False)
        self.horario = _make_horario(
            self.agenda, dia_semana=0, vagas=2,
        )

    def test_disponibilidade_sem_autenticacao_ca04(self):
        """CA-04: sem token, retorna 200 com contagens."""
        resp = self.client.get(
            '/api/v1/publico/agenda/agenda-pub-ok/disponibilidade/?de=2026-10-19&ate=2026-10-19',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Deve retornar o slot da segunda (2026-10-19 e segunda)
        self.assertEqual(len(resp.data), 1)
        slot = resp.data[0]
        self.assertEqual(slot['vagas'], 2)
        self.assertEqual(slot['vagas_ocupadas'], 0)
        self.assertEqual(slot['vagas_disponiveis'], 2)
        # Nao expoe nome/telefone de outros (RN-05)
        self.assertNotIn('nome_contato', slot)
        self.assertNotIn('telefone_contato', slot)

    def test_agenda_privada_retorna_404_ca07(self):
        """CA-07: agenda sem permite_agendamento_publico retorna 404."""
        resp = self.client.get(
            '/api/v1/publico/agenda/agenda-privada/disponibilidade/?de=2026-10-19&ate=2026-10-19',
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_intervalo_acima_60_dias_retorna_400(self):
        resp = self.client.get(
            '/api/v1/publico/agenda/agenda-pub-ok/disponibilidade/?de=2026-10-01&ate=2026-12-15',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_horario_privado_nao_aparece_na_disponibilidade(self):
        """Horario com publico=False nao aparece no endpoint publico."""
        _make_horario(self.agenda, dia_semana=0, hora='11:00', publico=False)
        resp = self.client.get(
            '/api/v1/publico/agenda/agenda-pub-ok/disponibilidade/?de=2026-10-19&ate=2026-10-19',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        horas = [s['hora_inicio'] for s in resp.data]
        self.assertNotIn('11:00', horas)

    def test_slot_lotado_aparece_com_flag(self):
        """Slot com 0 vagas aparece com lotado=True."""
        # Preencher as 2 vagas via ORM
        data = date(2026, 10, 19)
        for i in range(2):
            Compromisso.objects.create(
                agenda=self.agenda, horario=self.horario, data_horario=data,
                inicio='2026-10-19T09:00:00Z', fim='2026-10-19T09:30:00Z',
                nome_contato=f'Pessoa {i}',
            )
        resp = self.client.get(
            '/api/v1/publico/agenda/agenda-pub-ok/disponibilidade/?de=2026-10-19&ate=2026-10-19',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        slot = resp.data[0]
        self.assertEqual(slot['vagas_disponiveis'], 0)
        self.assertTrue(slot['lotado'])


class AgendamentoPublicoAPITest(APITestCase):
    """CA-05 / CA-08: endpoint publico de agendamento."""

    def setUp(self):
        cache.clear()
        self.agenda = _make_agenda_slug('Agenda Agendar', 'agenda-agendar', publica=True)
        self.horario = _make_horario(self.agenda, dia_semana=0, vagas=3)  # segunda

    def test_agendar_sem_token_ca05(self):
        """CA-05: POST sem token retorna 201 com origem=PUBLICO."""
        resp = self.client.post(
            '/api/v1/publico/agenda/agenda-agendar/agendar/',
            {
                'horario_id': self.horario.id,
                'data_horario': '2026-10-19',  # segunda
                'nome_contato': 'Joao Silva',
                'telefone_contato': '34991349194',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', resp.data)
        self.assertIn('mensagem', resp.data)
        comp = Compromisso.objects.get(pk=resp.data['id'])
        self.assertEqual(comp.origem, 'PUBLICO')
        self.assertIsNone(comp.cliente)

    def test_telefone_curto_retorna_400_ca05(self):
        """CA-05: telefone com menos de 8 digitos retorna 400."""
        resp = self.client.post(
            '/api/v1/publico/agenda/agenda-agendar/agendar/',
            {
                'horario_id': self.horario.id,
                'data_horario': '2026-10-19',
                'nome_contato': 'Joao',
                'telefone_contato': '123',  # < 8 digitos
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dia_semana_errado_retorna_400_ca08(self):
        """CA-08: data em dia diferente do dia_semana do horario retorna 400."""
        resp = self.client.post(
            '/api/v1/publico/agenda/agenda-agendar/agendar/',
            {
                'horario_id': self.horario.id,
                'data_horario': '2026-10-20',  # terca, nao segunda
                'nome_contato': 'Maria',
                'telefone_contato': '34991349194',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_horario_outro_slug_retorna_400(self):
        """Horario que nao pertence ao slug informado retorna 400."""
        outra = _make_agenda_slug('Outra', 'outra-agenda-ag', publica=True)
        h2 = _make_horario(outra, dia_semana=0, vagas=2)
        resp = self.client.post(
            '/api/v1/publico/agenda/agenda-agendar/agendar/',
            {
                'horario_id': h2.id,  # horario de outra agenda
                'data_horario': '2026-10-19',
                'nome_contato': 'Teste',
                'telefone_contato': '34991349194',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_agenda_privada_retorna_404(self):
        agenda_priv = _make_agenda_slug('Priv', 'agenda-priv', publica=False)
        h = _make_horario(agenda_priv, dia_semana=0)
        resp = self.client.post(
            '/api/v1/publico/agenda/agenda-priv/agendar/',
            {
                'horario_id': h.id,
                'data_horario': '2026-10-19',
                'nome_contato': 'Teste',
                'telefone_contato': '34991349194',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_horario_inativo_retorna_400(self):
        h_inativo = _make_horario(self.agenda, dia_semana=0, hora='10:00', ativo=False)
        resp = self.client.post(
            '/api/v1/publico/agenda/agenda-agendar/agendar/',
            {
                'horario_id': h_inativo.id,
                'data_horario': '2026-10-19',
                'nome_contato': 'Teste',
                'telefone_contato': '34991349194',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(DEFAULT_THROTTLE_RATES={'anon': '10/hour', 'user': '1000/day'})
class ThrottlePublicoTest(APITestCase):
    """CA-06: throttle por IP retorna 429 na 11a requisicao."""

    def setUp(self):
        cache.clear()
        self.agenda = _make_agenda_slug('Agenda Throttle', 'agenda-throttle', publica=True)
        self.horario = _make_horario(self.agenda, dia_semana=0, vagas=50)

    def test_throttle_11a_requisicao_ca06(self):
        cache.clear()
        url = '/api/v1/publico/agenda/agenda-throttle/disponibilidade/?de=2026-10-19&ate=2026-10-19'
        for i in range(10):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, status.HTTP_200_OK, f'Requisicao {i+1} falhou')
        # 11a deve ser bloqueada
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class AvisoConflitoAPITest(APITestCase):
    """CA-10: aviso de conflito de horario para mesmo cliente."""

    def setUp(self):
        self.user = _make_user('conflito@teste.com')
        self.client.force_authenticate(self.user)
        self.agenda = _make_agenda_slug('Agenda Conflito', 'agenda-conflito')

    def test_aviso_conflito_segundo_compromisso_ca10(self):
        """CA-10: segundo compromisso para o mesmo cliente no mesmo periodo retorna aviso."""
        from clientes.models import Cliente
        cliente = Cliente.objects.create(nome_razao_social='Cliente Conflito')

        # Primeiro — deve criar sem aviso
        resp1 = self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': self.agenda.id,
            'titulo': 'Compromisso 1',
            'cliente': cliente.id,
            'inicio': '2026-10-19T10:00:00Z',
            'fim': '2026-10-19T11:00:00Z',
        }, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('aviso', resp1.data)

        # Segundo — mesmo periodo, deve criar mas retornar aviso
        resp2 = self.client.post('/api/v1/agendamento/compromissos/', {
            'agenda': self.agenda.id,
            'titulo': 'Compromisso 2',
            'cliente': cliente.id,
            'inicio': '2026-10-19T10:30:00Z',
            'fim': '2026-10-19T11:30:00Z',
        }, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertIn('aviso', resp2.data)


@override_settings(DEFAULT_THROTTLE_RATES={'anon': '10/hour', 'user': '1000/day'})
class VagaConcorrentesTest(TransactionTestCase):
    """
    CA-03: Teste de concorrencia com threading.
    TransactionTestCase e obrigatorio — TestCase envolve tudo em rollback
    global que impede threads de verem mudancas umas das outras.
    """

    def setUp(self):
        cache.clear()
        self.agenda = Agenda.objects.create(
            nome='Agenda Conc',
            slug='agenda-conc',
            permite_agendamento_publico=True,
        )
        self.horario = HorarioDisponivel.objects.create(
            agenda=self.agenda,
            dia_semana=0,  # Segunda
            hora_inicio='09:00',
            duracao_minutos=30,
            vagas=2,
            servico='Consulta',
            publico=True,
            ativo=True,
        )
        self.data = date(2026, 10, 19)  # Uma segunda-feira

    def _tentar_agendar(self, nome, resultados, idx):
        """Executado por cada thread. Guarda o status_code no array."""
        client = APIClient()
        resp = client.post(
            '/api/v1/publico/agenda/agenda-conc/agendar/',
            {
                'horario_id': self.horario.id,
                'data_horario': str(self.data),
                'nome_contato': nome,
                'telefone_contato': '34991349194',
            },
            format='json',
        )
        resultados[idx] = resp.status_code
        connection.close()  # Fechar conexao da thread

    def test_concorrencia_max_vagas_ca03(self):
        """
        Dispara 3 threads simultaneas para horario de 2 vagas.
        Esperado: exatamente 2x201 e 1x400 (sem race condition).
        """
        resultados = [None, None, None]
        threads = [
            threading.Thread(
                target=self._tentar_agendar,
                args=(f'Contato {i}', resultados, i),
            )
            for i in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        criados = resultados.count(201)
        rejeitados = resultados.count(400)
        self.assertEqual(criados, 2, f'Esperado 2 criados, obteve {resultados}')
        self.assertEqual(rejeitados, 1, f'Esperado 1 rejeitado, obteve {resultados}')

        # Confirmar no banco
        total = Compromisso.objects.filter(
            horario=self.horario,
            data_horario=self.data,
            is_active=True,
        ).exclude(status='CANCELADO').count()
        self.assertEqual(total, 2)
