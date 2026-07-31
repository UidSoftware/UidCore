"""Testes do app clientes — Fase A da Manutenção #11.

Cobre: campos cpf/cnpj, AcionistaCliente, endpoints de acionistas.
"""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import AcionistaCliente, Cliente


def _make_user(email='admin@teste.com'):
    return User.objects.create_user(email=email, password='senha123', nome_completo='Admin Teste')


def _make_cliente_pj(nome='Empresa Teste'):
    return Cliente.objects.create(
        nome_razao_social=nome, tipo_pessoa='PJ', cnpj='12345678000190',
    )


def _make_cliente_pf(nome='Pessoa Teste'):
    return Cliente.objects.create(
        nome_razao_social=nome, tipo_pessoa='PF', cpf='12345678901',
    )


class ClienteCpfCnpjModelTest(TestCase):
    def test_cliente_pj_armazena_cnpj(self):
        cliente = _make_cliente_pj()
        cliente.refresh_from_db()
        self.assertEqual(cliente.cnpj, '12345678000190')
        self.assertEqual(cliente.cpf, '')

    def test_cliente_pf_armazena_cpf(self):
        cliente = _make_cliente_pf()
        cliente.refresh_from_db()
        self.assertEqual(cliente.cpf, '12345678901')
        self.assertEqual(cliente.cnpj, '')

    def test_campo_documento_ainda_existe(self):
        # Garantir que documento nao foi removido (compatibilidade)
        cliente = Cliente.objects.create(
            nome_razao_social='Compat', tipo_pessoa='PJ',
            documento='12345678000199',
        )
        self.assertIsNotNone(cliente.documento)


class AcionistaClienteModelTest(TestCase):
    def setUp(self):
        self.cliente = _make_cliente_pj()

    def test_criar_acionista_basico(self):
        ac = AcionistaCliente.objects.create(
            cliente=self.cliente, nome='João Silva', email='joao@teste.com',
            cpf='11122233344',
        )
        self.assertEqual(ac.nome, 'João Silva')
        self.assertEqual(ac.cliente, self.cliente)
        self.assertFalse(ac.principal)

    def test_principal_true_desmarca_outros(self):
        ac1 = AcionistaCliente.objects.create(
            cliente=self.cliente, nome='Sócio 1', principal=True,
        )
        ac2 = AcionistaCliente.objects.create(
            cliente=self.cliente, nome='Sócio 2', principal=True,
        )
        ac1.refresh_from_db()
        # ac2 é principal; ac1 deve ter sido desmarcado
        self.assertFalse(ac1.principal)
        self.assertTrue(ac2.principal)

    def test_soft_delete_via_is_active(self):
        ac = AcionistaCliente.objects.create(cliente=self.cliente, nome='Para Remover')
        ac.is_active = False
        ac.save()
        self.assertFalse(AcionistaCliente.objects.get(pk=ac.pk).is_active)


class AcionistaClienteAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.cliente = _make_cliente_pj()

    def test_listar_acionistas_get(self):
        AcionistaCliente.objects.create(cliente=self.cliente, nome='Sócio A')
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/acionistas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_criar_acionista_post(self):
        resp = self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/acionistas/',
            {'nome': 'Novo Sócio', 'email': 'socio@teste.com', 'principal': True},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', resp.data)

    def test_patch_acionista(self):
        ac = AcionistaCliente.objects.create(cliente=self.cliente, nome='Old Name')
        resp = self.client.patch(
            f'/api/v1/clientes/{self.cliente.id}/acionistas/{ac.id}/',
            {'nome': 'New Name'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['nome'], 'New Name')

    def test_delete_acionista_soft_delete(self):
        ac = AcionistaCliente.objects.create(cliente=self.cliente, nome='Para Deletar')
        resp = self.client.delete(f'/api/v1/clientes/{self.cliente.id}/acionistas/{ac.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        ac.refresh_from_db()
        self.assertFalse(ac.is_active)

    def test_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/acionistas/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cpf_cnpj_no_serializer_cliente(self):
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('cpf', resp.data)
        self.assertIn('cnpj', resp.data)
        self.assertIn('acionistas', resp.data)
