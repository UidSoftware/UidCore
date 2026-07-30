"""Testes do app portal (Fase E.6 -- Manutencao #7).

Cobre RF-PO01 a RF-PO03 e RN-PO01 a RN-PO03 da Especificacao_Hotfix.md.
"""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from clientes.models import Cliente

from .models import AcessoPortalCliente


def _make_user(email='admin@teste.com'):
    return User.objects.create_user(email=email, password='senha123', nome_completo='Admin Teste')


def _make_cliente(nome='Cliente Teste'):
    return Cliente.objects.create(nome_razao_social=nome, tipo_pessoa='PJ')


class AcessoPortalClienteModelTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            email='cliente@teste.com', password='senha123', nome_completo='Cliente Usuario',
        )
        self.cliente = _make_cliente()

    def test_criar_acesso_rf_po01(self):
        acesso = AcessoPortalCliente.objects.create(usuario=self.usuario, cliente=self.cliente)
        self.assertTrue(acesso.is_active)

    def test_usuario_e_onetoone_rn_po01(self):
        AcessoPortalCliente.objects.create(usuario=self.usuario, cliente=self.cliente)
        outro_cliente = _make_cliente(nome='Outro Cliente')
        with self.assertRaises(Exception):
            AcessoPortalCliente.objects.create(usuario=self.usuario, cliente=outro_cliente)

    def test_herda_base_model_tem_is_active_e_created_at_rn_po03(self):
        acesso = AcessoPortalCliente.objects.create(usuario=self.usuario, cliente=self.cliente)
        self.assertTrue(hasattr(acesso, 'is_active'))
        self.assertTrue(hasattr(acesso, 'created_at'))
        self.assertTrue(acesso.is_active)


class AcessoPortalClienteAPITest(APITestCase):
    def setUp(self):
        self.admin = _make_user()
        self.client.force_authenticate(self.admin)
        self.cliente = _make_cliente()
        self.usuario_portal = User.objects.create_user(
            email='portal@teste.com', password='senha123', nome_completo='Usuario Portal',
        )

    def test_criar_acesso_via_api_rf_po01(self):
        resp = self.client.post('/api/v1/portal/acessos/', {
            'usuario': self.usuario_portal.id, 'cliente': self.cliente.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['usuario_email'], 'portal@teste.com')

    def test_destroy_faz_soft_delete_via_campo_ativo_rf_po02(self):
        acesso = AcessoPortalCliente.objects.create(usuario=self.usuario_portal, cliente=self.cliente)
        resp = self.client.delete(f'/api/v1/portal/acessos/{acesso.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        acesso.refresh_from_db()
        self.assertFalse(acesso.is_active)

    def test_listar_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/portal/acessos/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
