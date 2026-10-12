"""Testes do app agendamento (Fase E.5 -- Manutencao #7).

Cobre RF-AG01 a RF-AG03 e RN-AG01 a RN-AG03 da Especificacao_Hotfix.md.
"""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import Agenda, Compromisso


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
