"""Testes do app vendas (Fase E.1 -- Manutencao #7 e Fase C -- Manutencao #11).

Cobre RF-V01 a RF-V03/V04, RN-V01 a RN-V03.
Cobre Fase C (Manutencao #11): ItemOrcamento, endpoints de itens de orcamento e pedido.
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from clientes.models import Cliente
from produtos.models import Produto

from .models import ItemOrcamento, ItemPedido, Orcamento, Pedido


def _make_user(email='admin@teste.com'):
    return User.objects.create_user(email=email, password='senha123', nome_completo='Admin Teste')


def _make_cliente(nome='Cliente Teste'):
    return Cliente.objects.create(nome_razao_social=nome, tipo_pessoa='PJ')


class OrcamentoModelTest(TestCase):
    def setUp(self):
        self.cliente = _make_cliente()

    def test_numeracao_automatica_orc_rf_v01(self):
        orc = Orcamento.objects.create(cliente=self.cliente, descricao='Orcamento teste')
        self.assertTrue(orc.numero.startswith('ORC-'))
        self.assertRegex(orc.numero, r'^ORC-\d{4}-\d{4}$')

    def test_numeracao_incrementa_sequencialmente(self):
        orc1 = Orcamento.objects.create(cliente=self.cliente, descricao='Um')
        orc2 = Orcamento.objects.create(cliente=self.cliente, descricao='Dois')
        seq1 = int(orc1.numero.split('-')[-1])
        seq2 = int(orc2.numero.split('-')[-1])
        self.assertEqual(seq2, seq1 + 1)

    def test_numero_manual_nao_e_sobrescrito_rn_v01(self):
        orc = Orcamento.objects.create(cliente=self.cliente, descricao='X', numero='ORC-2026-9999')
        orc.descricao = 'Atualizado'
        orc.save()
        orc.refresh_from_db()
        self.assertEqual(orc.numero, 'ORC-2026-9999')

    def test_soft_delete_nao_remove_do_banco(self):
        orc = Orcamento.objects.create(cliente=self.cliente, descricao='Y')
        orc_id = orc.id
        orc.is_active = False
        orc.save()
        self.assertTrue(Orcamento.objects.filter(pk=orc_id).exists())
        self.assertEqual(Orcamento.objects.get(pk=orc_id).is_active, False)


class PedidoModelTest(TestCase):
    def setUp(self):
        self.cliente = _make_cliente()

    def test_numeracao_automatica_ped_rf_v02(self):
        ped = Pedido.objects.create(cliente=self.cliente, data_pedido='2026-07-20')
        self.assertRegex(ped.numero, r'^PED-\d{4}-\d{4}$')

    def test_orcamento_opcional(self):
        ped = Pedido.objects.create(cliente=self.cliente, data_pedido='2026-07-20')
        self.assertIsNone(ped.orcamento)


class ItemPedidoModelTest(TestCase):
    def setUp(self):
        self.cliente = _make_cliente()
        self.pedido = Pedido.objects.create(cliente=self.cliente, data_pedido='2026-07-20')

    def test_valor_total_calculado_no_save_rf_v03(self):
        item = ItemPedido.objects.create(
            pedido=self.pedido, descricao='Produto X', quantidade=3, valor_unitario=Decimal('25.50'),
        )
        self.assertEqual(item.valor_total, Decimal('76.50'))

    def test_valor_total_recalculado_ao_atualizar_quantidade_rn_v02(self):
        item = ItemPedido.objects.create(
            pedido=self.pedido, descricao='Produto Y', quantidade=2, valor_unitario=Decimal('10.00'),
        )
        item.quantidade = 5
        item.save()
        item.refresh_from_db()
        self.assertEqual(item.valor_total, Decimal('50.00'))


class OrcamentoAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.cliente = _make_cliente()

    def test_criar_orcamento_via_api(self):
        resp = self.client.post('/api/v1/vendas/orcamentos/', {
            'cliente': self.cliente.id, 'descricao': 'Proposta comercial', 'valor_total': '1500.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['numero'].startswith('ORC-'))
        self.assertIn('id', resp.data)

    def test_listar_orcamentos_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/vendas/orcamentos/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_destroy_faz_soft_delete(self):
        orc = Orcamento.objects.create(cliente=self.cliente, descricao='Del')
        resp = self.client.delete(f'/api/v1/vendas/orcamentos/{orc.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        orc.refresh_from_db()
        self.assertFalse(orc.is_active)
        # Nao aparece mais na listagem
        resp = self.client.get('/api/v1/vendas/orcamentos/')
        ids = [o['id'] for o in resp.data['results']]
        self.assertNotIn(orc.id, ids)


class PedidoAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.cliente = _make_cliente()

    def test_criar_pedido_via_api_rf_v04(self):
        resp = self.client.post('/api/v1/vendas/pedidos/', {
            'cliente': self.cliente.id, 'data_pedido': '2026-07-20', 'valor_total': '500.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['numero'].startswith('PED-'))

    def test_destroy_pedido_faz_soft_delete(self):
        ped = Pedido.objects.create(cliente=self.cliente, data_pedido='2026-07-20')
        resp = self.client.delete(f'/api/v1/vendas/pedidos/{ped.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        ped.refresh_from_db()
        self.assertFalse(ped.is_active)


# --- Fase C (Manutenção #11): ItemOrcamento e itens de pedido inline ------

def _make_produto(nome='Produto Vendas Teste'):
    return Produto.objects.create(
        nome=nome, unidade_base='UN',
        valor_unitario=Decimal('10.00'), preco_venda=Decimal('15.00'),
    )


class ItemOrcamentoModelTest(TestCase):
    def setUp(self):
        self.cliente = _make_cliente()
        self.orc = Orcamento.objects.create(cliente=self.cliente, descricao='Orc Itens')

    def test_valor_total_calculado_no_save(self):
        item = ItemOrcamento.objects.create(
            orcamento=self.orc, descricao='Item A',
            quantidade=Decimal('3'), valor_unitario=Decimal('20.00'),
        )
        self.assertEqual(item.valor_total, Decimal('60.00'))

    def test_descricao_preenchida_pelo_produto_quando_vazia(self):
        produto = _make_produto(nome='Produto Auto')
        item = ItemOrcamento.objects.create(
            orcamento=self.orc, produto=produto,
            descricao='',  # vazio — deve ser preenchido pelo produto
            quantidade=Decimal('1'), valor_unitario=Decimal('10.00'),
        )
        self.assertEqual(item.descricao, 'Produto Auto')

    def test_descricao_manual_nao_e_sobrescrita_pelo_produto(self):
        produto = _make_produto(nome='Produto X')
        item = ItemOrcamento.objects.create(
            orcamento=self.orc, produto=produto,
            descricao='Desc Manual',
            quantidade=Decimal('1'), valor_unitario=Decimal('5.00'),
        )
        self.assertEqual(item.descricao, 'Desc Manual')


class ItensOrcamentoAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.cliente = _make_cliente()
        self.orc = Orcamento.objects.create(cliente=self.cliente, descricao='ORC API')

    def test_listar_itens_orcamento(self):
        ItemOrcamento.objects.create(
            orcamento=self.orc, descricao='Item 1',
            quantidade=Decimal('2'), valor_unitario=Decimal('10.00'),
        )
        resp = self.client.get(f'/api/v1/vendas/orcamentos/{self.orc.id}/itens/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_criar_item_orcamento(self):
        resp = self.client.post(
            f'/api/v1/vendas/orcamentos/{self.orc.id}/itens/',
            {'descricao': 'Novo Item', 'quantidade': '2.000', 'valor_unitario': '50.00'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['valor_total'], '100.00')

    def test_patch_item_orcamento(self):
        item = ItemOrcamento.objects.create(
            orcamento=self.orc, descricao='Item PATCH',
            quantidade=Decimal('1'), valor_unitario=Decimal('10.00'),
        )
        resp = self.client.patch(
            f'/api/v1/vendas/orcamentos/{self.orc.id}/itens/{item.id}/',
            {'quantidade': '3.000', 'valor_unitario': '10.00'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['valor_total'], '30.00')

    def test_delete_item_orcamento_soft_delete(self):
        item = ItemOrcamento.objects.create(
            orcamento=self.orc, descricao='Del',
            quantidade=Decimal('1'), valor_unitario=Decimal('5.00'),
        )
        resp = self.client.delete(f'/api/v1/vendas/orcamentos/{self.orc.id}/itens/{item.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        item.refresh_from_db()
        self.assertFalse(item.is_active)

    def test_orcamento_serializer_inclui_itens(self):
        ItemOrcamento.objects.create(
            orcamento=self.orc, descricao='Serializer Item',
            quantidade=Decimal('1'), valor_unitario=Decimal('100.00'),
        )
        resp = self.client.get(f'/api/v1/vendas/orcamentos/{self.orc.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('itens', resp.data)
        self.assertEqual(len(resp.data['itens']), 1)


class ItensPedidoInlineAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.cliente = _make_cliente()
        self.ped = Pedido.objects.create(cliente=self.cliente, data_pedido='2026-07-31')

    def test_criar_item_pedido_inline(self):
        resp = self.client.post(
            f'/api/v1/vendas/pedidos/{self.ped.id}/itens/',
            {'descricao': 'Item Pedido', 'quantidade': '5.000', 'valor_unitario': '20.00'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['valor_total'], '100.00')

    def test_pedido_serializer_inclui_itens(self):
        ItemPedido.objects.create(
            pedido=self.ped, descricao='Item',
            quantidade=Decimal('2'), valor_unitario=Decimal('10.00'),
        )
        resp = self.client.get(f'/api/v1/vendas/pedidos/{self.ped.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('itens', resp.data)
        self.assertEqual(len(resp.data['itens']), 1)
