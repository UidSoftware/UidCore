"""Testes do app produtos — Fase B da Manutenção #11.

Cobre: Produto, ConversaoUnidade, EntradaEstoque (com conversão de unidade),
endpoints /produtos/, /produtos/{id}/conversoes/, /produtos/{id}/entradas/.
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import ConversaoUnidade, EntradaEstoque, Produto


def _make_user(email='admin@teste.com'):
    return User.objects.create_user(email=email, password='senha123', nome_completo='Admin Teste')


def _make_produto(nome='Produto Teste', unidade_base='UN'):
    return Produto.objects.create(
        nome=nome, unidade_base=unidade_base,
        valor_unitario=Decimal('10.00'), preco_venda=Decimal('15.00'),
    )


class ProdutoModelTest(TestCase):
    def test_criar_produto_basico(self):
        p = _make_produto()
        self.assertEqual(p.nome, 'Produto Teste')
        self.assertEqual(p.quantidade_estoque, Decimal('0'))
        self.assertTrue(p.is_active)

    def test_soft_delete(self):
        p = _make_produto()
        p.is_active = False
        p.save()
        self.assertFalse(Produto.objects.get(pk=p.pk).is_active)


class ConversaoUnidadeModelTest(TestCase):
    def setUp(self):
        self.produto = _make_produto(unidade_base='UN')

    def test_criar_conversao(self):
        conv = ConversaoUnidade.objects.create(
            produto=self.produto, unidade='CX', quantidade_por_base=Decimal('12'),
        )
        self.assertEqual(conv.unidade, 'CX')
        self.assertEqual(conv.quantidade_por_base, Decimal('12'))

    def test_unique_together_produto_unidade(self):
        ConversaoUnidade.objects.create(produto=self.produto, unidade='CX', quantidade_por_base=12)
        from django.db import IntegrityError
        with self.assertRaises(Exception):
            ConversaoUnidade.objects.create(produto=self.produto, unidade='CX', quantidade_por_base=6)


class EntradaEstoqueModelTest(TestCase):
    def setUp(self):
        self.produto = _make_produto(unidade_base='UN')
        ConversaoUnidade.objects.create(
            produto=self.produto, unidade='CX', quantidade_por_base=Decimal('12'),
        )

    def test_entrada_na_unidade_base_atualiza_estoque(self):
        EntradaEstoque.objects.create(
            produto=self.produto, quantidade=Decimal('10'), unidade='UN',
        )
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('10'))

    def test_entrada_com_conversao_atualiza_estoque_em_base(self):
        EntradaEstoque.objects.create(
            produto=self.produto, quantidade=Decimal('2'), unidade='CX',
        )
        self.produto.refresh_from_db()
        # 2 CX * 12 UN/CX = 24 UN
        self.assertEqual(self.produto.quantidade_estoque, Decimal('24'))

    def test_entrada_sem_conversao_assume_1_para_1(self):
        """Unidade sem conversão definida usa quantidade_base = quantidade."""
        EntradaEstoque.objects.create(
            produto=self.produto, quantidade=Decimal('5'), unidade='KG',
        )
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('5'))

    def test_quantidade_base_salva_corretamente(self):
        entrada = EntradaEstoque.objects.create(
            produto=self.produto, quantidade=Decimal('3'), unidade='CX',
        )
        entrada.refresh_from_db()
        self.assertEqual(entrada.quantidade_base, Decimal('36'))


class ProdutoAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)

    def test_criar_produto_via_api(self):
        resp = self.client.post('/api/v1/produtos/', {
            'nome': 'Produto API', 'unidade_base': 'UN',
            'valor_unitario': '5.00', 'preco_venda': '8.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', resp.data)
        self.assertIn('conversoes', resp.data)

    def test_listar_produtos(self):
        _make_produto()
        resp = self.client.get('/api/v1/produtos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data['results']), 1)

    def test_destroy_soft_delete(self):
        p = _make_produto()
        resp = self.client.delete(f'/api/v1/produtos/{p.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        p.refresh_from_db()
        self.assertFalse(p.is_active)

    def test_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/produtos/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_criar_conversao_endpoint(self):
        p = _make_produto()
        resp = self.client.post(
            f'/api/v1/produtos/{p.id}/conversoes/',
            {'unidade': 'CX', 'quantidade_por_base': '12.000'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['unidade'], 'CX')

    def test_criar_entrada_endpoint_atualiza_estoque(self):
        p = _make_produto()
        resp = self.client.post(
            f'/api/v1/produtos/{p.id}/entradas/',
            {'quantidade': '10.000', 'unidade': 'UN'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        p.refresh_from_db()
        self.assertEqual(p.quantidade_estoque, Decimal('10'))

    def test_search_por_nome(self):
        _make_produto(nome='Caneta Azul')
        _make_produto(nome='Borracha')
        resp = self.client.get('/api/v1/produtos/?search=Caneta')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        nomes = [r['nome'] for r in resp.data['results']]
        self.assertIn('Caneta Azul', nomes)
        self.assertNotIn('Borracha', nomes)
