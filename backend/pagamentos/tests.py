"""Testes do app pagamentos (Fase E.2 -- Manutencao #7).

Cobre RF-P01 a RF-P03 e RN-P01 a RN-P03 da Especificacao_Hotfix.md.
"""
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from clientes.models import Cliente

from .models import Cobranca, MetodoPagamento, Parcela


def _make_user(email='admin@teste.com'):
    return User.objects.create_user(email=email, password='senha123', nome_completo='Admin Teste')


def _make_cliente(nome='Cliente Teste'):
    return Cliente.objects.create(nome_razao_social=nome, tipo_pessoa='PJ')


class MetodoPagamentoModelTest(TestCase):
    def test_criar_metodo_rf_p01(self):
        metodo = MetodoPagamento.objects.create(nome='PIX')
        self.assertEqual(metodo.get_nome_display(), 'PIX')

    def test_nome_unico(self):
        MetodoPagamento.objects.create(nome='PIX')
        with self.assertRaises(Exception):
            MetodoPagamento.objects.create(nome='PIX')


class CobrancaModelTest(TestCase):
    def setUp(self):
        self.cliente = _make_cliente()

    def test_criar_cobranca_valor_decimal_rf_p02(self):
        cobranca = Cobranca.objects.create(
            cliente=self.cliente, descricao='Mensalidade', valor=Decimal('199.90'),
            vencimento='2026-07-30',
        )
        self.assertIsInstance(cobranca.valor, Decimal)

    def test_soft_delete_rn_p03(self):
        cobranca = Cobranca.objects.create(
            cliente=self.cliente, descricao='Mensalidade', valor=Decimal('50.00'),
            vencimento='2026-07-30',
        )
        cobranca.is_active = False
        cobranca.save()
        self.assertTrue(Cobranca.objects.filter(pk=cobranca.pk).exists())


class ParcelaModelTest(TestCase):
    def setUp(self):
        self.cliente = _make_cliente()
        self.cobranca = Cobranca.objects.create(
            cliente=self.cliente, descricao='Compra parcelada', valor=Decimal('300.00'),
            vencimento='2026-07-30',
        )

    def test_criar_parcela_vinculada_a_cobranca_rf_p03(self):
        parcela = Parcela.objects.create(
            cobranca=self.cobranca, numero=1, valor=Decimal('100.00'), vencimento='2026-08-01',
        )
        self.assertEqual(parcela.cobranca, self.cobranca)


class CobrancaAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.cliente = _make_cliente()
        self.metodo = MetodoPagamento.objects.create(nome='PIX')

    def test_criar_cobranca_com_comprovante_multipart_rn_p01(self):
        comprovante = SimpleUploadedFile('comprovante.pdf', b'conteudo fake', content_type='application/pdf')
        resp = self.client.post('/api/v1/pagamentos/cobrancas/', {
            'cliente': self.cliente.id, 'descricao': 'Servico X', 'valor': '250.00',
            'vencimento': '2026-08-05', 'metodo': self.metodo.id, 'comprovante': comprovante,
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_destroy_faz_soft_delete_rn_p03(self):
        cobranca = Cobranca.objects.create(
            cliente=self.cliente, descricao='Del', valor=Decimal('10.00'), vencimento='2026-07-30',
        )
        resp = self.client.delete(f'/api/v1/pagamentos/cobrancas/{cobranca.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        cobranca.refresh_from_db()
        self.assertFalse(cobranca.is_active)

    def test_listar_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/pagamentos/cobrancas/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class MetodoPagamentoAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)

    def test_crud_metodos_rf_p01(self):
        resp = self.client.post('/api/v1/pagamentos/metodos/', {'nome': 'BOLETO'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        metodo_id = resp.data['id']

        resp = self.client.delete(f'/api/v1/pagamentos/metodos/{metodo_id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        metodo = MetodoPagamento.objects.get(pk=metodo_id)
        self.assertFalse(metodo.is_active)


class ParcelaAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.cliente = _make_cliente()
        self.cobranca = Cobranca.objects.create(
            cliente=self.cliente, descricao='Compra parcelada', valor=Decimal('300.00'),
            vencimento='2026-07-30',
        )

    def test_criar_parcela_via_api_rf_p03(self):
        resp = self.client.post('/api/v1/pagamentos/parcelas/', {
            'cobranca': self.cobranca.id, 'numero': 1, 'valor': '150.00', 'vencimento': '2026-08-10',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
