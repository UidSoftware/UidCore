"""
Testes do app compras — Manutencao #58 (Fase 2).

Cobre RF-01 a RF-10 e RN-01 a RN-08 da Especificacao_Hotfix.md, ponta a
ponta via API real (nao mocka MovimentoEstoque/Despesa/LivroCaixa — usa os
mecanismos ja em producao das Fases 1/anteriores).
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from financeiro.models import Categoria, Conta, Despesa, LivroCaixa
from fornecedores.models import Fornecedor
from produtos.models import ConversaoUnidade, MovimentoEstoque, Produto

from .models import Compra, ItemCompra, StatusCompra


def _make_user(email='admin@teste.com', is_staff=True):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Admin Teste', is_staff=is_staff,
    )


def _make_fornecedor(nome='Fornecedor Teste'):
    return Fornecedor.objects.create(nome_razao_social=nome, tipo_pessoa='PJ', cnpj='11222333000181')


def _make_conta(nome='Conta Teste', saldo_inicial=Decimal('1000.00')):
    return Conta.objects.create(nome=nome, tipo='CORRENTE', saldo_inicial=saldo_inicial)


def _make_produto(nome='Produto Teste', unidade_base='UN', valor_unitario=Decimal('1.00')):
    return Produto.objects.create(nome=nome, unidade_base=unidade_base, valor_unitario=valor_unitario)


def _make_categoria_compra():
    # RF-09: a migration 0002_categoria_compra_mercadoria ja semeia essa
    # Categoria via RunPython — get_or_create evita duplicidade
    # (unique_together nome+tipo) no banco de teste, que roda as migrations
    # normalmente antes de cada suite.
    categoria, _ = Categoria.objects.get_or_create(nome='Compra de Mercadoria', tipo='SAIDA')
    return categoria


class CompraModelTest(TestCase):
    def setUp(self):
        self.fornecedor = _make_fornecedor()
        self.conta = _make_conta()
        self.produto = _make_produto()

    def test_criar_compra_calcula_subtotal_item(self):
        compra = Compra.objects.create(
            fornecedor=self.fornecedor, conta=self.conta,
            data_emissao='2026-09-01', status=StatusCompra.PENDENTE,
            valor_total=Decimal('50.00'),
        )
        item = ItemCompra.objects.create(
            compra=compra, produto=self.produto, quantidade=Decimal('5'),
            unidade='UN', valor_unitario_custo=Decimal('10.00'),
        )
        self.assertEqual(item.subtotal, Decimal('50.00'))

    def test_criar_item_compra_gera_movimento_estoque_entrada(self):
        compra = Compra.objects.create(
            fornecedor=self.fornecedor, conta=self.conta,
            data_emissao='2026-09-01', status=StatusCompra.PENDENTE,
            valor_total=Decimal('50.00'),
        )
        item = ItemCompra.objects.create(
            compra=compra, produto=self.produto, quantidade=Decimal('5'),
            unidade='UN', valor_unitario_custo=Decimal('10.00'),
        )
        item.refresh_from_db()
        self.assertIsNotNone(item.movimento_estoque)
        self.assertEqual(item.movimento_estoque.tipo, 'ENTRADA')
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('5'))
        # RF-05: ultimo custo sobrescreve Produto.valor_unitario
        self.assertEqual(self.produto.valor_unitario, Decimal('10.00'))

    def test_soft_delete_compra(self):
        compra = Compra.objects.create(
            fornecedor=self.fornecedor, conta=self.conta,
            data_emissao='2026-09-01', valor_total=Decimal('0'),
        )
        compra.is_active = False
        compra.save()
        self.assertFalse(Compra.objects.get(pk=compra.pk).is_active)


class CompraSignalDespesaTest(TestCase):
    def setUp(self):
        self.fornecedor = _make_fornecedor()
        self.conta = _make_conta()
        _make_categoria_compra()

    def test_criar_compra_pendente_gera_despesa_pendente_sem_livro_caixa(self):
        compra = Compra.objects.create(
            fornecedor=self.fornecedor, conta=self.conta,
            data_emissao='2026-09-01', status=StatusCompra.PENDENTE,
            valor_total=Decimal('100.00'),
        )
        compra.refresh_from_db()
        self.assertIsNotNone(compra.despesa)
        despesa = compra.despesa
        self.assertEqual(despesa.status, 'PENDENTE')
        self.assertIsNone(despesa.pagamento)
        self.assertEqual(despesa.categoria.nome, 'Compra de Mercadoria')
        self.assertEqual(despesa.fornecedor, self.fornecedor.nome_razao_social)
        self.assertEqual(despesa.valor_bruto, Decimal('100.00'))
        self.assertFalse(
            LivroCaixa.objects.filter(origem='DESPESA', origem_id=despesa.id).exists()
        )

    def test_criar_compra_paga_gera_despesa_paga_com_livro_caixa(self):
        compra = Compra.objects.create(
            fornecedor=self.fornecedor, conta=self.conta,
            data_emissao='2026-09-01', status=StatusCompra.PAGO,
            valor_total=Decimal('100.00'),
        )
        compra.refresh_from_db()
        despesa = compra.despesa
        self.assertEqual(despesa.status, 'PAGO')
        self.assertEqual(despesa.pagamento.isoformat(), '2026-09-01')
        lc = LivroCaixa.objects.filter(origem='DESPESA', origem_id=despesa.id).first()
        self.assertIsNotNone(lc)
        self.assertEqual(lc.valor, despesa.valor_liquido)


class CompraAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.fornecedor = _make_fornecedor()
        self.conta = _make_conta()
        _make_categoria_compra()
        self.produto1 = _make_produto(nome='Produto 1')
        self.produto2 = _make_produto(nome='Produto 2')

    def _payload(self, status_inicial='PENDENTE'):
        return {
            'fornecedor': self.fornecedor.id,
            'conta': self.conta.id,
            'numero_nota_fiscal': 'NF-001',
            'data_emissao': '2026-09-01',
            'forma_pagamento': 'PIX',
            'status': status_inicial,
            'observacoes': '',
            'itens': [
                {
                    'produto': self.produto1.id,
                    'quantidade': '2',
                    'unidade': 'UN',
                    'valor_unitario_custo': '10.00',
                },
                {
                    'produto': self.produto2.id,
                    'quantidade': '3',
                    'unidade': 'UN',
                    'valor_unitario_custo': '5.00',
                },
            ],
        }

    def test_ca01_criar_compra_valor_total_bate_soma_itens(self):
        resp = self.client.post('/api/v1/compras/', self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        compra = Compra.objects.get(pk=resp.data['id'])
        # 2*10 + 3*5 = 35.00
        self.assertEqual(compra.valor_total, Decimal('35.00'))

    def test_ca02_movimentos_estoque_e_quantidade_atualizada(self):
        resp = self.client.post('/api/v1/compras/', self._payload(), format='json')
        compra = Compra.objects.get(pk=resp.data['id'])
        self.assertEqual(
            MovimentoEstoque.objects.filter(produto=self.produto1, tipo='ENTRADA').count(), 1,
        )
        self.assertEqual(
            MovimentoEstoque.objects.filter(produto=self.produto2, tipo='ENTRADA').count(), 1,
        )
        self.produto1.refresh_from_db()
        self.produto2.refresh_from_db()
        self.assertEqual(self.produto1.quantidade_estoque, Decimal('2'))
        self.assertEqual(self.produto2.quantidade_estoque, Decimal('3'))

    def test_ca03_produto_valor_unitario_atualizado(self):
        self.client.post('/api/v1/compras/', self._payload(), format='json')
        self.produto1.refresh_from_db()
        self.produto2.refresh_from_db()
        self.assertEqual(self.produto1.valor_unitario, Decimal('10.00'))
        self.assertEqual(self.produto2.valor_unitario, Decimal('5.00'))

    def test_ca04_despesa_criada_com_categoria_e_fornecedor_corretos(self):
        resp = self.client.post('/api/v1/compras/', self._payload(), format='json')
        compra = Compra.objects.get(pk=resp.data['id'])
        despesa = compra.despesa
        self.assertIsNotNone(despesa)
        self.assertEqual(despesa.categoria.nome, 'Compra de Mercadoria')
        self.assertEqual(despesa.valor_bruto, compra.valor_total)
        self.assertEqual(despesa.fornecedor, self.fornecedor.nome_razao_social)
        self.assertEqual(despesa.status, 'PENDENTE')

    def test_ca05_compra_pendente_despesa_pendente_sem_livro_caixa(self):
        resp = self.client.post('/api/v1/compras/', self._payload('PENDENTE'), format='json')
        compra = Compra.objects.get(pk=resp.data['id'])
        despesa = compra.despesa
        self.assertEqual(despesa.status, 'PENDENTE')
        self.assertIsNone(despesa.pagamento)
        self.assertFalse(
            LivroCaixa.objects.filter(origem='DESPESA', origem_id=despesa.id).exists()
        )

    def test_ca06_compra_paga_gera_livro_caixa(self):
        resp = self.client.post('/api/v1/compras/', self._payload('PAGO'), format='json')
        compra = Compra.objects.get(pk=resp.data['id'])
        despesa = compra.despesa
        self.assertEqual(despesa.status, 'PAGO')
        self.assertEqual(despesa.pagamento.isoformat(), '2026-09-01')
        lc = LivroCaixa.objects.get(origem='DESPESA', origem_id=despesa.id)
        self.assertEqual(lc.valor, despesa.valor_liquido)

    def test_ca07_patch_status_pendente_para_pago_gera_livro_caixa(self):
        resp = self.client.post('/api/v1/compras/', self._payload('PENDENTE'), format='json')
        compra_id = resp.data['id']
        patch_resp = self.client.patch(f'/api/v1/compras/{compra_id}/', {'status': 'PAGO'}, format='json')
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK, patch_resp.data)
        compra = Compra.objects.get(pk=compra_id)
        despesa = compra.despesa
        despesa.refresh_from_db()
        self.assertEqual(despesa.status, 'PAGO')
        self.assertTrue(LivroCaixa.objects.filter(origem='DESPESA', origem_id=despesa.id).exists())

    def test_ca08_patch_ignora_fornecedor_conta_itens(self):
        resp = self.client.post('/api/v1/compras/', self._payload('PENDENTE'), format='json')
        compra_id = resp.data['id']
        outro_fornecedor = _make_fornecedor(nome='Outro Fornecedor')
        outra_conta = _make_conta(nome='Outra Conta')
        patch_resp = self.client.patch(
            f'/api/v1/compras/{compra_id}/',
            {
                'status': 'PAGO',
                'fornecedor': outro_fornecedor.id,
                'conta': outra_conta.id,
                'itens': [],
            },
            format='json',
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK, patch_resp.data)
        compra = Compra.objects.get(pk=compra_id)
        self.assertEqual(compra.fornecedor_id, self.fornecedor.id)
        self.assertEqual(compra.conta_id, self.conta.id)
        self.assertEqual(compra.itens.count(), 2)

    def test_ca09_patch_status_cancelado_bloqueado(self):
        resp = self.client.post('/api/v1/compras/', self._payload('PENDENTE'), format='json')
        compra_id = resp.data['id']
        patch_resp = self.client.patch(f'/api/v1/compras/{compra_id}/', {'status': 'CANCELADO'}, format='json')
        self.assertEqual(patch_resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ca10_cancelar_compra_paga_reverte_estoque_e_estorna_despesa(self):
        resp = self.client.post('/api/v1/compras/', self._payload('PAGO'), format='json')
        compra_id = resp.data['id']
        compra = Compra.objects.get(pk=compra_id)
        despesa = compra.despesa
        self.assertTrue(LivroCaixa.objects.filter(origem='DESPESA', origem_id=despesa.id).exists())

        cancel_resp = self.client.post(f'/api/v1/compras/{compra_id}/cancelar/')
        self.assertEqual(cancel_resp.status_code, status.HTTP_200_OK, cancel_resp.data)

        compra.refresh_from_db()
        self.assertEqual(compra.status, StatusCompra.CANCELADO)

        self.produto1.refresh_from_db()
        self.produto2.refresh_from_db()
        self.assertEqual(self.produto1.quantidade_estoque, Decimal('0'))
        self.assertEqual(self.produto2.quantidade_estoque, Decimal('0'))

        despesa.refresh_from_db()
        self.assertTrue(despesa.estornado)
        self.assertTrue(
            LivroCaixa.objects.filter(origem='ESTORNO', origem_id=despesa.id, estornado=True).exists()
        )

    def test_ca11_cancelar_compra_pendente_reverte_estoque_e_soft_delete_despesa(self):
        resp = self.client.post('/api/v1/compras/', self._payload('PENDENTE'), format='json')
        compra_id = resp.data['id']
        compra = Compra.objects.get(pk=compra_id)
        despesa = compra.despesa

        cancel_resp = self.client.post(f'/api/v1/compras/{compra_id}/cancelar/')
        self.assertEqual(cancel_resp.status_code, status.HTTP_200_OK, cancel_resp.data)

        compra.refresh_from_db()
        self.assertEqual(compra.status, StatusCompra.CANCELADO)

        self.produto1.refresh_from_db()
        self.produto2.refresh_from_db()
        self.assertEqual(self.produto1.quantidade_estoque, Decimal('0'))
        self.assertEqual(self.produto2.quantidade_estoque, Decimal('0'))

        despesa.refresh_from_db()
        self.assertFalse(despesa.is_active)
        self.assertFalse(LivroCaixa.objects.filter(origem='ESTORNO', origem_id=despesa.id).exists())

    def test_ca12_cancelar_compra_ja_cancelada_400(self):
        resp = self.client.post('/api/v1/compras/', self._payload('PENDENTE'), format='json')
        compra_id = resp.data['id']
        self.client.post(f'/api/v1/compras/{compra_id}/cancelar/')
        cancel_resp2 = self.client.post(f'/api/v1/compras/{compra_id}/cancelar/')
        self.assertEqual(cancel_resp2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ca13_unidade_sem_conversao_400_rollback_completo(self):
        payload = self._payload()
        payload['itens'][0]['unidade'] = 'CX'  # sem ConversaoUnidade cadastrada
        resp = self.client.post('/api/v1/compras/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Compra.objects.count(), 0)
        self.assertEqual(Despesa.objects.count(), 0)
        self.assertEqual(MovimentoEstoque.objects.count(), 0)

    def test_ca13b_com_conversao_cadastrada_funciona(self):
        ConversaoUnidade.objects.create(
            produto=self.produto1, unidade='CX', quantidade_por_base=Decimal('12'),
        )
        payload = self._payload()
        payload['itens'][0]['unidade'] = 'CX'
        resp = self.client.post('/api/v1/compras/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.produto1.refresh_from_db()
        # 2 CX * 12 UN/CX = 24 UN
        self.assertEqual(self.produto1.quantidade_estoque, Decimal('24'))

    def test_ca14_sem_itens_400(self):
        payload = self._payload()
        payload['itens'] = []
        resp = self.client.post('/api/v1/compras/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ca15_quantidade_ou_valor_zero_400(self):
        payload = self._payload()
        payload['itens'][0]['quantidade'] = '0'
        resp = self.client.post('/api/v1/compras/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        payload = self._payload()
        payload['itens'][0]['valor_unitario_custo'] = '0'
        resp = self.client.post('/api/v1/compras/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ca16_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/compras/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ca16_sem_perfil_admin_403(self):
        user_comum = _make_user(email='comum@teste.com', is_staff=False)
        self.client.force_authenticate(user_comum)
        resp = self.client.get('/api/v1/compras/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_nao_permitido(self):
        resp = self.client.post('/api/v1/compras/', self._payload(), format='json')
        compra_id = resp.data['id']
        put_resp = self.client.put(f'/api/v1/compras/{compra_id}/', self._payload(), format='json')
        self.assertEqual(put_resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_nao_permitido(self):
        resp = self.client.post('/api/v1/compras/', self._payload(), format='json')
        compra_id = resp.data['id']
        del_resp = self.client.delete(f'/api/v1/compras/{compra_id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class EstornarDespesaRegressaoTest(APITestCase):
    """CA-17 — extracao de estornar_despesa() para services.py nao pode
    quebrar o endpoint ja existente DespesaViewSet.estornar_despesa."""

    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.conta = _make_conta()
        self.categoria = Categoria.objects.create(nome='Aluguel', tipo='SAIDA')

    def test_estornar_despesa_endpoint_ainda_funciona(self):
        despesa = Despesa.objects.create(
            tipo='FIXA', descricao='Aluguel Setembro', valor_bruto=Decimal('500.00'),
            conta=self.conta, categoria=self.categoria,
            vencimento='2026-09-05', pagamento='2026-09-05', status='PAGO',
        )
        self.assertTrue(LivroCaixa.objects.filter(origem='DESPESA', origem_id=despesa.id).exists())

        resp = self.client.post(
            f'/api/v1/financeiro/despesas/{despesa.id}/estornar/',
            {'motivo': 'Pagamento em duplicidade'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        despesa.refresh_from_db()
        self.assertTrue(despesa.estornado)
        self.assertTrue(
            LivroCaixa.objects.filter(origem='ESTORNO', origem_id=despesa.id, estornado=True).exists()
        )

    def test_estornar_despesa_ja_estornada_400(self):
        despesa = Despesa.objects.create(
            tipo='FIXA', descricao='Aluguel', valor_bruto=Decimal('500.00'),
            conta=self.conta, categoria=self.categoria,
            vencimento='2026-09-05', pagamento='2026-09-05', status='PAGO',
            estornado=True,
        )
        resp = self.client.post(
            f'/api/v1/financeiro/despesas/{despesa.id}/estornar/',
            {'motivo': 'teste'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_estornar_despesa_sem_motivo_400(self):
        despesa = Despesa.objects.create(
            tipo='FIXA', descricao='Aluguel', valor_bruto=Decimal('500.00'),
            conta=self.conta, categoria=self.categoria,
            vencimento='2026-09-05', pagamento='2026-09-05', status='PAGO',
        )
        resp = self.client.post(
            f'/api/v1/financeiro/despesas/{despesa.id}/estornar/',
            {'motivo': ''}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class AuditoriaManutencao62APITest(APITestCase):
    """Manutencao 62 — created_by (create)/updated_by (PATCH status). Compra
    nao tem DELETE exposto (RN-05, imutavel exceto status) — sem ciclo de
    destroy aqui."""

    def setUp(self):
        self.fornecedor = _make_fornecedor()
        self.conta = _make_conta()
        _make_categoria_compra()
        self.produto = _make_produto()

    def _payload(self, status_inicial='PENDENTE'):
        return {
            'fornecedor': self.fornecedor.id,
            'conta': self.conta.id,
            'numero_nota_fiscal': 'NF-AUD-001',
            'data_emissao': '2026-09-01',
            'forma_pagamento': 'PIX',
            'status': status_inicial,
            'observacoes': '',
            'itens': [
                {
                    'produto': self.produto.id,
                    'quantidade': '1',
                    'unidade': 'UN',
                    'valor_unitario_custo': '10.00',
                },
            ],
        }

    def test_create_grava_created_by_e_patch_status_grava_updated_by(self):
        user_a = _make_user(email='a62compras@teste.com')
        user_b = _make_user(email='b62compras@teste.com')

        self.client.force_authenticate(user_a)
        resp = self.client.post('/api/v1/compras/', self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        compra_id = resp.data['id']
        compra = Compra.objects.get(pk=compra_id)
        self.assertEqual(compra.created_by, user_a)
        self.assertIsNone(compra.updated_by)

        self.client.force_authenticate(user_b)
        resp = self.client.patch(f'/api/v1/compras/{compra_id}/', {'status': 'PAGO'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        compra.refresh_from_db()
        self.assertEqual(compra.updated_by, user_b)
        self.assertEqual(compra.created_by, user_a)
