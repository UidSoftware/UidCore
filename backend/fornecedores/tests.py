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
