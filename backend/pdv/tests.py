"""
pdv/tests.py — Suite de testes do modulo PDV.

Cobertura obrigatoria (Sentinel — RF-01 a RF-16):
  RF-01/02 : abrir_sessao OK + bloqueio sessao duplicada (RN-01)
  RF-03/04 : adicionar item ao carrinho (snapshot de preco)
  RF-05    : sessao atual do operador logado
  RF-06-09 : finalizar venda (DINHEIRO, split, sem estoque, sem sessao)
  RF-10    : movimento de caixa (sangria/suprimento)
  RF-11    : fechar sessao (sem bloquear por diferenca — RN-07)
  RF-12    : cancelar venda (RN-08 — estoque volta)
  RF-13    : devolver item parcialmente (Ponto 2)
  RF-16    : autenticacao obrigatoria (401 sem token)
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from clientes.models import Cliente
from financeiro.models import Categoria, Conta, Receita
from pagamentos.models import MetodoPagamento, NomeMetodoPagamento
from produtos.models import Produto

from .models import (
    ItemVenda,
    MovimentoCaixa,
    PagamentoVenda,
    SessaoCaixa,
    Venda,
)
from .services import abrir_sessao, fechar_sessao, finalizar_venda


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _criar_usuario(email='admin@pdv.test', nome='Admin PDV', is_staff=True):
    u = User.objects.create_user(
        email=email,
        password='Senha@123',
        nome_completo=nome,
    )
    u.is_staff = is_staff
    u.save(update_fields=['is_staff'])
    return u


def _criar_conta(nome='Caixa PDV', tipo='CAIXA'):
    return Conta.objects.create(nome=nome, tipo=tipo, saldo_inicial=Decimal('0'))


def _criar_metodo(nome='DINHEIRO'):
    metodo, _ = MetodoPagamento.objects.get_or_create(nome=nome)
    return metodo


def _criar_produto(nome='Produto Teste', preco=Decimal('10.00'), estoque=Decimal('10')):
    return Produto.objects.create(
        nome=nome,
        preco_venda=preco,
        quantidade_estoque=estoque,
        unidade_base='UN',
    )


def _criar_categoria():
    cat, _ = Categoria.objects.get_or_create(
        nome='Vendas PDV', tipo='ENTRADA',
    )
    return cat


def _criar_cliente(nome='Cliente Teste PDV'):
    return Cliente.objects.create(nome_razao_social=nome)


# ---------------------------------------------------------------------------
# Testes de servico (unit)
# ---------------------------------------------------------------------------

class AbrirSessaoServiceTest(TestCase):
    """RF-01 — abrir_sessao()"""

    def setUp(self):
        self.usuario = _criar_usuario()
        self.conta = _criar_conta()

    def test_abrir_sessao_ok(self):
        sessao = abrir_sessao(
            conta_id=self.conta.id,
            valor_abertura=Decimal('100.00'),
            usuario=self.usuario,
        )
        self.assertEqual(sessao.status, 'ABERTA')
        self.assertEqual(sessao.conta, self.conta)
        self.assertEqual(sessao.operador, self.usuario)
        self.assertEqual(sessao.valor_abertura, Decimal('100.00'))

    def test_abrir_sessao_bloqueada_se_ja_existe(self):
        """RN-01: no maximo 1 sessao ABERTA por conta."""
        abrir_sessao(
            conta_id=self.conta.id,
            valor_abertura=Decimal('0'),
            usuario=self.usuario,
        )
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            abrir_sessao(
                conta_id=self.conta.id,
                valor_abertura=Decimal('0'),
                usuario=self.usuario,
            )

    def test_fechar_sessao_calcula_diferenca(self):
        """RF-11 / RN-07: nao bloqueia por diferenca, apenas registra."""
        sessao = abrir_sessao(
            conta_id=self.conta.id,
            valor_abertura=Decimal('100.00'),
            usuario=self.usuario,
        )
        sessao_fechada = fechar_sessao(
            sessao=sessao,
            valor_fechamento_informado=Decimal('90.00'),
        )
        self.assertEqual(sessao_fechada.status, 'FECHADA')
        self.assertIsNotNone(sessao_fechada.data_fechamento)
        self.assertEqual(sessao_fechada.valor_fechamento_informado, Decimal('90.00'))


# ---------------------------------------------------------------------------
# Testes de API (integration)
# ---------------------------------------------------------------------------

class PDVAPITestBase(APITestCase):
    """Base com setUp comum a todos os testes de API do PDV."""

    def setUp(self):
        self.usuario = _criar_usuario()
        self.conta = _criar_conta()
        self.conta_pix = _criar_conta('Conta PIX', 'CORRENTE')
        self.metodo_dinheiro = _criar_metodo('DINHEIRO')
        self.metodo_pix = _criar_metodo('PIX')
        self.produto = _criar_produto()
        self.categoria = _criar_categoria()

        # Autenticar
        resp = self.client.post('/api/v1/auth/token/', {
            'email': self.usuario.email,
            'password': 'Senha@123',
        })
        self.assertEqual(resp.status_code, 200, resp.data)
        token = resp.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def _abrir_sessao(self, conta=None, valor=Decimal('0')):
        conta = conta or self.conta
        resp = self.client.post('/api/v1/pdv/sessoes/', {
            'conta': conta.id,
            'valor_abertura': str(valor),
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        return resp.data

    def _criar_venda(self):
        resp = self.client.post('/api/v1/pdv/vendas/', {})
        self.assertEqual(resp.status_code, 201, resp.data)
        return resp.data

    def _adicionar_item(self, venda_id, produto=None, qtd='1', desconto='0'):
        produto = produto or self.produto
        resp = self.client.post(f'/api/v1/pdv/vendas/{venda_id}/itens/', {
            'produto': produto.id,
            'quantidade': qtd,
            'unidade': 'UN',
            'desconto_item': desconto,
        })
        return resp


class SessaoCaixaAPITest(PDVAPITestBase):
    """Testes de sessao de caixa via API."""

    def test_sessao_atual_sem_sessao_aberta(self):
        """GET /sessoes/atual/ sem sessao retorna {'sessao': None}."""
        resp = self.client.get('/api/v1/pdv/sessoes/atual/')
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data.get('sessao'))

    def test_sessao_atual_com_sessao_aberta(self):
        """GET /sessoes/atual/ retorna dados da sessao aberta."""
        self._abrir_sessao(valor=Decimal('50.00'))
        resp = self.client.get('/api/v1/pdv/sessoes/atual/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'ABERTA')

    def test_abrir_sessao_via_api(self):
        """POST /sessoes/ — RF-01."""
        resp = self.client.post('/api/v1/pdv/sessoes/', {
            'conta': self.conta.id,
            'valor_abertura': '100.00',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['status'], 'ABERTA')
        self.assertEqual(resp.data['conta'], self.conta.id)

    def test_abrir_sessao_duplicada_retorna_400(self):
        """RN-01: POST /sessoes/ com sessao ja aberta → 400."""
        self._abrir_sessao()
        resp = self.client.post('/api/v1/pdv/sessoes/', {
            'conta': self.conta.id,
            'valor_abertura': '0',
        })
        self.assertEqual(resp.status_code, 400)

    def test_sangria_em_sessao_aberta(self):
        """RF-10: POST /sessoes/{id}/movimento/ tipo=SANGRIA → 201."""
        sessao = self._abrir_sessao()
        resp = self.client.post(f'/api/v1/pdv/sessoes/{sessao["id"]}/movimento/', {
            'tipo': 'SANGRIA',
            'valor': '20.00',
            'motivo': 'Sangria para cofre',
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['tipo'], 'SANGRIA')

    def test_fechar_sessao(self):
        """RF-11: POST /sessoes/{id}/fechar/ → status=FECHADA."""
        sessao = self._abrir_sessao(valor=Decimal('100.00'))
        resp = self.client.post(f'/api/v1/pdv/sessoes/{sessao["id"]}/fechar/', {
            'valor_fechamento_informado': '90.00',
            'observacoes': 'Diferenca de R$10',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'FECHADA')

    def test_sem_autenticacao_retorna_401(self):
        """RF-16: sem token → 401."""
        self.client.credentials()
        resp = self.client.get('/api/v1/pdv/sessoes/')
        self.assertEqual(resp.status_code, 401)


class VendaAPITest(PDVAPITestBase):
    """Testes de venda via API."""

    def setUp(self):
        super().setUp()
        self._abrir_sessao()

    def test_criar_venda_com_sessao_aberta(self):
        """POST /vendas/ — RF-02, cria venda ABERTA."""
        resp = self.client.post('/api/v1/pdv/vendas/', {})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['status'], 'ABERTA')
        self.assertTrue(resp.data['numero'].startswith('VDA-'))

    def test_criar_venda_sem_sessao_retorna_400(self):
        """RF-02: sem sessao aberta → 400."""
        # Fechar sessao
        sess_resp = self.client.get('/api/v1/pdv/sessoes/atual/')
        sessao_id = sess_resp.data['id']
        self.client.post(f'/api/v1/pdv/sessoes/{sessao_id}/fechar/', {
            'valor_fechamento_informado': '0',
        })
        resp = self.client.post('/api/v1/pdv/vendas/', {})
        self.assertEqual(resp.status_code, 400)

    def test_adicionar_item_ao_carrinho(self):
        """RF-03/04: POST /vendas/{id}/itens/ — adiciona item com snapshot de preco."""
        venda = self._criar_venda()
        resp = self._adicionar_item(venda['id'])
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Decimal(resp.data['valor_unitario']), self.produto.preco_venda)
        self.assertEqual(resp.data['produto'], self.produto.id)

    def test_finalizar_venda_dinheiro(self):
        """RF-06-09: finalizar com DINHEIRO — estoque debitado, Receita criada."""
        venda = self._criar_venda()
        self._adicionar_item(venda['id'])
        resp = self.client.post(f'/api/v1/pdv/vendas/{venda["id"]}/finalizar/', {
            'pagamentos': [
                {
                    'metodo': self.metodo_dinheiro.id,
                    'valor': '10.00',
                    'conta': self.conta.id,
                }
            ]
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'FINALIZADA')

        # Estoque debitado
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('9'))

        # Receita criada e ja recebida
        self.assertTrue(
            Receita.objects.filter(
                conta=self.conta, status='RECEBIDO',
            ).exists()
        )

    def test_finalizar_venda_split_dois_pagamentos(self):
        """RF-07: split 2 metodos — 2 Receitas criadas."""
        venda = self._criar_venda()
        self._adicionar_item(venda['id'])
        resp = self.client.post(f'/api/v1/pdv/vendas/{venda["id"]}/finalizar/', {
            'pagamentos': [
                {
                    'metodo': self.metodo_dinheiro.id,
                    'valor': '5.00',
                    'conta': self.conta.id,
                },
                {
                    'metodo': self.metodo_pix.id,
                    'valor': '5.00',
                    'conta': self.conta_pix.id,
                },
            ]
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['status'], 'FINALIZADA')
        self.assertEqual(len(resp.data['pagamentos']), 2)

        receitas_count = Receita.objects.filter(status='RECEBIDO').count()
        self.assertEqual(receitas_count, 2)

    def test_finalizar_venda_sem_estoque_retorna_400(self):
        """RF-06: produto sem estoque → 400."""
        self.produto.quantidade_estoque = Decimal('0')
        self.produto.save()

        venda = self._criar_venda()
        self._adicionar_item(venda['id'])
        resp = self.client.post(f'/api/v1/pdv/vendas/{venda["id"]}/finalizar/', {
            'pagamentos': [
                {
                    'metodo': self.metodo_dinheiro.id,
                    'valor': '10.00',
                    'conta': self.conta.id,
                }
            ]
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_cancelar_venda_finalizada_devolve_estoque(self):
        """RF-12 / RN-08: cancelar venda FINALIZADA — estoque voltando."""
        venda = self._criar_venda()
        self._adicionar_item(venda['id'])
        resp_fin = self.client.post(f'/api/v1/pdv/vendas/{venda["id"]}/finalizar/', {
            'pagamentos': [
                {
                    'metodo': self.metodo_dinheiro.id,
                    'valor': '10.00',
                    'conta': self.conta.id,
                }
            ]
        }, format='json')
        self.assertEqual(resp_fin.status_code, 200)

        # Cancela
        resp_can = self.client.post(f'/api/v1/pdv/vendas/{venda["id"]}/cancelar/', {
            'motivo': 'Teste cancelamento'
        }, format='json')
        self.assertEqual(resp_can.status_code, 200, resp_can.data)
        self.assertEqual(resp_can.data['status'], 'CANCELADA')

        # Estoque voltou
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('10'))

    def test_cancelar_venda_aberta_ok(self):
        """RF-12: cancelar venda ABERTA diretamente."""
        venda = self._criar_venda()
        resp = self.client.post(f'/api/v1/pdv/vendas/{venda["id"]}/cancelar/', {
            'motivo': 'Erro operacional'
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'CANCELADA')

    def test_devolver_item_parcial(self):
        """RF-13 / Ponto 2: devolucao parcial de item — estoque volta proporcional."""
        venda = self._criar_venda()
        # Adicionar 2 unidades
        resp_item = self._adicionar_item(venda['id'], qtd='2')
        self.assertEqual(resp_item.status_code, 201)

        # Finalizar com pagamento de R$20 (2 x R$10)
        resp_fin = self.client.post(f'/api/v1/pdv/vendas/{venda["id"]}/finalizar/', {
            'pagamentos': [
                {
                    'metodo': self.metodo_dinheiro.id,
                    'valor': '20.00',
                    'conta': self.conta.id,
                }
            ]
        }, format='json')
        self.assertEqual(resp_fin.status_code, 200, resp_fin.data)
        venda_id = resp_fin.data['id']

        # Obter pagamento e item criados
        venda_detail = self.client.get(f'/api/v1/pdv/vendas/{venda_id}/')
        pagamento_id = venda_detail.data['pagamentos'][0]['id']
        item_id = venda_detail.data['itens'][0]['id']

        # Devolver 1 das 2 unidades
        resp_dev = self.client.post(
            f'/api/v1/pdv/vendas/{venda_id}/itens/{item_id}/devolver/',
            {'quantidade': '1', 'motivo': 'Produto com defeito', 'pagamento_id': pagamento_id},
            format='json',
        )
        self.assertEqual(resp_dev.status_code, 200, resp_dev.data)
        self.assertEqual(Decimal(resp_dev.data['quantidade_estornada']), Decimal('1'))

        # Estoque: era 10, vendeu 2 → ficou 8; devolveu 1 → agora 9
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('9'))

    def test_venda_sem_autenticacao_retorna_401(self):
        """RF-16: endpoint de venda sem token → 401."""
        self.client.credentials()
        resp = self.client.get('/api/v1/pdv/vendas/')
        self.assertEqual(resp.status_code, 401)

    # ── Testes de PATCH (RF-17 post-fix Manutenção #22) ─────────────────────

    def test_vincular_cliente_via_patch(self):
        """PATCH /vendas/{id}/ {cliente: id} vincula cliente à venda ABERTA."""
        venda = self._criar_venda()
        cliente = _criar_cliente()

        resp = self.client.patch(
            f'/api/v1/pdv/vendas/{venda["id"]}/',
            {'cliente': cliente.id},
            format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['cliente'], cliente.id)
        self.assertEqual(resp.data['cliente_nome'], cliente.nome_razao_social)

        # Confirmar no banco
        Venda.objects.get(pk=venda['id'], cliente=cliente)  # não levanta DoesNotExist

    def test_desvincular_cliente_via_patch(self):
        """PATCH /vendas/{id}/ {cliente: null} desvincula cliente da venda."""
        venda = self._criar_venda()
        cliente = _criar_cliente()

        # Vincular primeiro
        self.client.patch(
            f'/api/v1/pdv/vendas/{venda["id"]}/',
            {'cliente': cliente.id},
            format='json',
        )

        # Desvincular
        resp = self.client.patch(
            f'/api/v1/pdv/vendas/{venda["id"]}/',
            {'cliente': None},
            format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIsNone(resp.data['cliente'])

        venda_db = Venda.objects.get(pk=venda['id'])
        self.assertIsNone(venda_db.cliente)

    def test_editar_quantidade_item_via_patch(self):
        """PATCH /vendas/{id}/itens/{item_id}/ edita quantidade e recalcula valor_total."""
        venda = self._criar_venda()
        resp_item = self._adicionar_item(venda['id'], qtd='1')
        self.assertEqual(resp_item.status_code, 201, resp_item.data)
        item_id = resp_item.data['id']

        preco_unitario = self.produto.preco_venda  # Decimal('10.00')

        resp = self.client.patch(
            f'/api/v1/pdv/vendas/{venda["id"]}/itens/{item_id}/',
            {'quantidade': '3'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(Decimal(resp.data['quantidade']), Decimal('3'))

        # valor_total da venda deve ter sido recalculado: 3 x R$10 = R$30
        venda_detail = self.client.get(f'/api/v1/pdv/vendas/{venda["id"]}/')
        self.assertEqual(Decimal(venda_detail.data['valor_total']), preco_unitario * 3)


class VendaEstornoReceitaAPITest(PDVAPITestBase):
    """Testes de estorno de receita apos finalizacao de venda PDV."""

    def setUp(self):
        super().setUp()
        self._abrir_sessao()

        # Criar venda e finalizar
        venda = self._criar_venda()
        self._adicionar_item(venda['id'])
        resp_fin = self.client.post(f'/api/v1/pdv/vendas/{venda["id"]}/finalizar/', {
            'pagamentos': [
                {
                    'metodo': self.metodo_dinheiro.id,
                    'valor': '10.00',
                    'conta': self.conta.id,
                }
            ]
        }, format='json')
        self.assertEqual(resp_fin.status_code, 200, resp_fin.data)
        self.receita = Receita.objects.filter(status='RECEBIDO').first()
        self.assertIsNotNone(self.receita)

    def test_estornar_receita_pdv_action(self):
        """POST /financeiro/receitas/{id}/estornar/ — admin pode estornar receita do PDV."""
        resp = self.client.post(f'/api/v1/financeiro/receitas/{self.receita.id}/estornar/', {
            'valor': str(self.receita.valor_liquido),
            'motivo': 'Devolucao completa do cliente',
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Decimal(resp.data['valor']), self.receita.valor_liquido)

    def test_estornar_receita_pendente_retorna_400(self):
        """RN-04: somente RECEBIDO pode ser estornado."""
        receita_pendente = Receita.objects.create(
            descricao='Pendente',
            valor_bruto=Decimal('50'),
            conta=self.conta,
            status='PENDENTE',
        )
        resp = self.client.post(f'/api/v1/financeiro/receitas/{receita_pendente.id}/estornar/', {
            'valor': '50',
            'motivo': 'Teste',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
