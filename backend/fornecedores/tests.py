"""Testes do app fornecedores — Fase A da Manutenção #11.

Cobre: campos cpf/cnpj, AcionistaFornecedor, endpoints de acionistas.
"""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import AcionistaFornecedor, Fornecedor


def _make_user(email='admin@teste.com'):
    return User.objects.create_user(email=email, password='senha123', nome_completo='Admin Teste')


def _make_fornecedor_pj(nome='Fornecedor PJ Teste'):
    return Fornecedor.objects.create(
        nome_razao_social=nome, tipo_pessoa='PJ', cnpj='98765432000100',
    )


class FornecedorCpfCnpjModelTest(TestCase):
    def test_fornecedor_pj_armazena_cnpj(self):
        forn = _make_fornecedor_pj()
        forn.refresh_from_db()
        self.assertEqual(forn.cnpj, '98765432000100')
        self.assertEqual(forn.cpf, '')

    def test_campo_documento_ainda_existe(self):
        forn = Fornecedor.objects.create(
            nome_razao_social='Compat', tipo_pessoa='PJ',
            documento='98765432000199',
        )
        self.assertIsNotNone(forn.documento)


class AcionistaFornecedorModelTest(TestCase):
    def setUp(self):
        self.forn = _make_fornecedor_pj()

    def test_criar_acionista_basico(self):
        ac = AcionistaFornecedor.objects.create(
            fornecedor=self.forn, nome='Maria Santos', email='maria@teste.com',
        )
        self.assertEqual(ac.nome, 'Maria Santos')
        self.assertFalse(ac.principal)

    def test_principal_true_desmarca_outros(self):
        ac1 = AcionistaFornecedor.objects.create(fornecedor=self.forn, nome='Sócio 1', principal=True)
        ac2 = AcionistaFornecedor.objects.create(fornecedor=self.forn, nome='Sócio 2', principal=True)
        ac1.refresh_from_db()
        self.assertFalse(ac1.principal)
        self.assertTrue(ac2.principal)


class AcionistaFornecedorAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.forn = _make_fornecedor_pj()

    def test_listar_acionistas_get(self):
        AcionistaFornecedor.objects.create(fornecedor=self.forn, nome='Sócio A')
        resp = self.client.get(f'/api/v1/fornecedores/{self.forn.id}/acionistas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_criar_acionista_post(self):
        resp = self.client.post(
            f'/api/v1/fornecedores/{self.forn.id}/acionistas/',
            {'nome': 'Novo Sócio', 'email': 'socio@forn.com'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', resp.data)

    def test_delete_acionista_soft_delete(self):
        ac = AcionistaFornecedor.objects.create(fornecedor=self.forn, nome='Para Deletar')
        resp = self.client.delete(f'/api/v1/fornecedores/{self.forn.id}/acionistas/{ac.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        ac.refresh_from_db()
        self.assertFalse(ac.is_active)

    def test_cpf_cnpj_e_acionistas_no_serializer_fornecedor(self):
        resp = self.client.get(f'/api/v1/fornecedores/{self.forn.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('cpf', resp.data)
        self.assertIn('cnpj', resp.data)
        self.assertIn('acionistas', resp.data)


class AuditoriaManutencao62APITest(APITestCase):
    """Manutencao 62 — ciclo completo created_by/updated_by/deleted_by/deleted_at."""

    def test_ciclo_completo_auditoria_fornecedor(self):
        user_a = _make_user(email='a62@teste.com')
        user_b = _make_user(email='b62@teste.com')
        user_c = _make_user(email='c62@teste.com')

        self.client.force_authenticate(user_a)
        resp = self.client.post('/api/v1/fornecedores/', {'nome_razao_social': 'Fornecedor Auditoria'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        forn_id = resp.data['id']
        forn = Fornecedor.objects.get(pk=forn_id)
        self.assertEqual(forn.created_by, user_a)

        self.client.force_authenticate(user_b)
        resp = self.client.patch(f'/api/v1/fornecedores/{forn_id}/', {'website': 'https://exemplo.com'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        forn.refresh_from_db()
        self.assertEqual(forn.updated_by, user_b)
        self.assertEqual(forn.created_by, user_a)

        self.client.force_authenticate(user_c)
        resp = self.client.delete(f'/api/v1/fornecedores/{forn_id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        forn = Fornecedor.all_objects.get(pk=forn_id)
        self.assertEqual(forn.deleted_by, user_c)
        self.assertIsNotNone(forn.deleted_at)
        self.assertFalse(Fornecedor.objects.filter(pk=forn_id).exists())
