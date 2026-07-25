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
        agenda = Agenda.objects.get(pk=agenda_id)
        self.assertFalse(agenda.is_active)
