"""Testes do app produtos — Fase B da Manutenção #11.

Cobre: Produto, ConversaoUnidade, EntradaEstoque (com conversão de unidade),
endpoints /produtos/, /produtos/{id}/conversoes/, /produtos/{id}/entradas/.
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import Combo, ConversaoUnidade, EntradaEstoque, ItemCombo, Produto


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

    def test_entrada_sem_conversao_rejeitada(self):
        """RN-05 (Manutencao 37): unidade sem conversão cadastrada NÃO faz
        mais fallback 1:1 silencioso — levanta ValidationError, estoque
        permanece intacto."""
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            EntradaEstoque.objects.create(
                produto=self.produto, quantidade=Decimal('5'), unidade='KG',
            )
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('0'))

    def test_quantidade_base_salva_corretamente(self):
        entrada = EntradaEstoque.objects.create(
            produto=self.produto, quantidade=Decimal('3'), unidade='CX',
        )
        entrada.refresh_from_db()
        self.assertEqual(entrada.quantidade_base, Decimal('36'))


class FatorParaBaseServiceTest(TestCase):
    """
    produtos/services.py::fator_para_base — Manutencao 37.
    Cadeia CX -> PT -> UN (1 CX = 6 PT ; 1 PT = 50 UN -> 1 CX = 300 UN).
    """

    def setUp(self):
        self.produto = _make_produto(unidade_base='UN')

    def test_cadeia_dois_elos_resolve_para_base(self):
        from .services import fator_para_base

        ConversaoUnidade.objects.create(
            produto=self.produto, unidade='PT', quantidade_por_base=Decimal('50'),
        )
        ConversaoUnidade.objects.create(
            produto=self.produto, unidade='CX', converte_para='PT', quantidade_por_base=Decimal('6'),
        )
        self.assertEqual(fator_para_base(self.produto, 'CX'), Decimal('300'))
        self.assertEqual(fator_para_base(self.produto, 'PT'), Decimal('50'))
        self.assertEqual(fator_para_base(self.produto, 'UN'), Decimal('1'))

    def test_ciclo_rejeitado(self):
        from django.core.exceptions import ValidationError
        from .services import fator_para_base

        ConversaoUnidade.objects.create(
            produto=self.produto, unidade='CX', converte_para='PT', quantidade_por_base=Decimal('6'),
        )
        ConversaoUnidade.objects.create(
            produto=self.produto, unidade='PT', converte_para='CX', quantidade_por_base=Decimal('2'),
        )
        with self.assertRaises(ValidationError):
            fator_para_base(self.produto, 'CX')

    def test_cadeia_sem_terminar_na_base_rejeitada(self):
        """CX aponta pra PT, mas PT nao tem conversao cadastrada — cadeia
        quebrada nunca chega na unidade_base (RN-01)."""
        from django.core.exceptions import ValidationError
        from .services import fator_para_base

        ConversaoUnidade.objects.create(
            produto=self.produto, unidade='CX', converte_para='PT', quantidade_por_base=Decimal('6'),
        )
        with self.assertRaises(ValidationError):
            fator_para_base(self.produto, 'CX')

    def test_unidade_sem_conversao_rejeitada(self):
        """RN-05: sem nenhuma ConversaoUnidade cadastrada para a unidade."""
        from django.core.exceptions import ValidationError
        from .services import fator_para_base

        with self.assertRaises(ValidationError):
            fator_para_base(self.produto, 'KG')


class EntradaEstoqueCadeiaTest(TestCase):
    """EntradaEstoque.save() usando cadeia de conversao (Manutencao 37)."""

    def setUp(self):
        self.produto = _make_produto(unidade_base='UN')
        ConversaoUnidade.objects.create(
            produto=self.produto, unidade='PT', quantidade_por_base=Decimal('50'),
        )
        ConversaoUnidade.objects.create(
            produto=self.produto, unidade='CX', converte_para='PT', quantidade_por_base=Decimal('6'),
        )

    def test_entrada_cadeia_dois_elos_atualiza_estoque_correto(self):
        entrada = EntradaEstoque.objects.create(
            produto=self.produto, quantidade=Decimal('1'), unidade='CX',
        )
        entrada.refresh_from_db()
        self.produto.refresh_from_db()
        # 1 CX = 6 PT = 300 UN
        self.assertEqual(entrada.quantidade_base, Decimal('300'))
        self.assertEqual(self.produto.quantidade_estoque, Decimal('300'))


class ConversaoUnidadeAPITest(APITestCase):
    """Endpoints /produtos/{id}/conversoes/ com cadeia (RF-01/RN-01/RN-03)."""

    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.produto = _make_produto(unidade_base='UN')

    def test_criar_conversao_cadeia_via_api(self):
        resp_pt = self.client.post(
            f'/api/v1/produtos/{self.produto.id}/conversoes/',
            {'unidade': 'PT', 'quantidade_por_base': '50'},
            format='json',
        )
        self.assertEqual(resp_pt.status_code, status.HTTP_201_CREATED, resp_pt.data)

        resp_cx = self.client.post(
            f'/api/v1/produtos/{self.produto.id}/conversoes/',
            {'unidade': 'CX', 'converte_para': 'PT', 'quantidade_por_base': '6'},
            format='json',
        )
        self.assertEqual(resp_cx.status_code, status.HTTP_201_CREATED, resp_cx.data)
        self.assertEqual(resp_cx.data['converte_para'], 'PT')

    def test_criar_cx_antes_de_pt_sem_pt_cadastrada_rejeitada_400(self):
        """Manutencao 40 — cenario exato relatado pelo usuario: criar CX
        (converte_para=PT, quantidade_por_base=6) ANTES de existir uma
        linha PT persistida. Confirma RN-04 da Especificacao_Hotfix.md:
        isso NAO e bug de backend — e o comportamento intencional (a
        cadeia so pode ser resolvida ate a unidade base se cada elo
        referenciado ja estiver persistido no momento do POST daquela
        linha). O fix do cenario completo do usuario fica no frontend
        (RF-02, ordenacao topologica das chamadas POST/PATCH antes de
        disparar), nao aqui."""
        resp_cx_primeiro = self.client.post(
            f'/api/v1/produtos/{self.produto.id}/conversoes/',
            {'unidade': 'CX', 'converte_para': 'PT', 'quantidade_por_base': '6'},
            format='json',
        )
        self.assertEqual(resp_cx_primeiro.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('PT', str(resp_cx_primeiro.data))

        # Criando PT primeiro (ordem correta) e depois CX apontando para
        # ela funciona normalmente — confirma que a resolucao da cadeia e
        # agnostica a ordem HISTORICA de criacao, so exige que a unidade
        # referenciada esteja persistida no momento exato do POST.
        resp_pt = self.client.post(
            f'/api/v1/produtos/{self.produto.id}/conversoes/',
            {'unidade': 'PT', 'quantidade_por_base': '50'},
            format='json',
        )
        self.assertEqual(resp_pt.status_code, status.HTTP_201_CREATED, resp_pt.data)

        resp_cx_depois = self.client.post(
            f'/api/v1/produtos/{self.produto.id}/conversoes/',
            {'unidade': 'CX', 'converte_para': 'PT', 'quantidade_por_base': '6'},
            format='json',
        )
        self.assertEqual(resp_cx_depois.status_code, status.HTTP_201_CREATED, resp_cx_depois.data)
        self.assertEqual(resp_cx_depois.data['converte_para'], 'PT')

    def test_criar_conversao_ciclo_rejeitada_400(self):
        self.client.post(
            f'/api/v1/produtos/{self.produto.id}/conversoes/',
            {'unidade': 'CX', 'converte_para': 'PT', 'quantidade_por_base': '6'},
            format='json',
        )
        resp = self.client.post(
            f'/api/v1/produtos/{self.produto.id}/conversoes/',
            {'unidade': 'PT', 'converte_para': 'CX', 'quantidade_por_base': '2'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_criar_conversao_sem_terminar_na_base_rejeitada_400(self):
        resp = self.client.post(
            f'/api/v1/produtos/{self.produto.id}/conversoes/',
            {'unidade': 'CX', 'converte_para': 'PT', 'quantidade_por_base': '6'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_conversao_soft_deletada_nao_aparece_no_produto_aninhado(self):
        """CA-03: campo 'conversoes' do ProdutoSerializer (GET /produtos/{id}/
        e GET /produtos/?search=) nunca deve expor conversão excluída —
        mesmo filtro do endpoint dedicado /produtos/{id}/conversoes/."""
        conv = ConversaoUnidade.objects.create(
            produto=self.produto, unidade='CX', quantidade_por_base=Decimal('12'),
        )
        resp = self.client.get(f'/api/v1/produtos/{self.produto.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['conversoes']), 1)

        conv.is_active = False
        conv.save(update_fields=['is_active', 'updated_at'])

        resp = self.client.get(f'/api/v1/produtos/{self.produto.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['conversoes'], [])

        resp_busca = self.client.get(f'/api/v1/produtos/?search={self.produto.nome}')
        self.assertEqual(resp_busca.status_code, status.HTTP_200_OK)
        produto_resp = next(r for r in resp_busca.data['results'] if r['id'] == self.produto.id)
        self.assertEqual(produto_resp['conversoes'], [])

    def test_recriar_conversao_apos_exclusao_reativa_sem_500(self):
        """Bug real: unique_together=(produto, unidade) não distingue
        is_active — criar, excluir (soft delete) e recriar a MESMA unidade
        batia em IntegrityError cru (500). Deve reativar o registro
        existente com os dados novos e responder 201."""
        resp_criar = self.client.post(
            f'/api/v1/produtos/{self.produto.id}/conversoes/',
            {'unidade': 'CX', 'quantidade_por_base': '12.000'},
            format='json',
        )
        self.assertEqual(resp_criar.status_code, status.HTTP_201_CREATED)
        conv_id = resp_criar.data['id']

        resp_excluir = self.client.delete(
            f'/api/v1/produtos/{self.produto.id}/conversoes/{conv_id}/',
        )
        self.assertEqual(resp_excluir.status_code, status.HTTP_204_NO_CONTENT)

        resp_recriar = self.client.post(
            f'/api/v1/produtos/{self.produto.id}/conversoes/',
            {'unidade': 'CX', 'quantidade_por_base': '24.000'},
            format='json',
        )
        self.assertEqual(resp_recriar.status_code, status.HTTP_201_CREATED, resp_recriar.data)
        self.assertEqual(resp_recriar.data['id'], conv_id)
        self.assertEqual(Decimal(resp_recriar.data['quantidade_por_base']), Decimal('24.000'))
        self.assertTrue(resp_recriar.data['is_active'])

        self.assertEqual(
            ConversaoUnidade.objects.filter(produto=self.produto, unidade='CX').count(), 1,
        )

        resp_listar = self.client.get(f'/api/v1/produtos/{self.produto.id}/conversoes/')
        self.assertEqual(len(resp_listar.data), 1)
        self.assertEqual(resp_listar.data[0]['id'], conv_id)

    def test_criar_conversao_duplicada_ativa_retorna_400(self):
        """Guarda-corpo: já existe conversão ATIVA pra mesma unidade —
        400 explícito, nunca IntegrityError (500)."""
        self.client.post(
            f'/api/v1/produtos/{self.produto.id}/conversoes/',
            {'unidade': 'CX', 'quantidade_por_base': '12.000'},
            format='json',
        )
        resp = self.client.post(
            f'/api/v1/produtos/{self.produto.id}/conversoes/',
            {'unidade': 'CX', 'quantidade_por_base': '99.000'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ConversaoUnidadeRN06Test(APITestCase):
    """Editar/excluir conversao usada como elo intermediario e bloqueado."""

    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.produto = _make_produto(unidade_base='UN')
        self.pt = ConversaoUnidade.objects.create(
            produto=self.produto, unidade='PT', quantidade_por_base=Decimal('50'),
        )
        self.cx = ConversaoUnidade.objects.create(
            produto=self.produto, unidade='CX', converte_para='PT', quantidade_por_base=Decimal('6'),
        )

    def test_excluir_elo_intermediario_bloqueado(self):
        resp = self.client.delete(
            f'/api/v1/produtos/{self.produto.id}/conversoes/{self.pt.id}/',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('dependentes', resp.data)
        self.pt.refresh_from_db()
        self.assertTrue(self.pt.is_active)

    def test_editar_elo_intermediario_bloqueado(self):
        resp = self.client.patch(
            f'/api/v1/produtos/{self.produto.id}/conversoes/{self.pt.id}/',
            {'quantidade_por_base': '60'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.pt.refresh_from_db()
        self.assertEqual(self.pt.quantidade_por_base, Decimal('50'))

    def test_excluir_conversao_sem_dependentes_permitido(self):
        resp = self.client.delete(
            f'/api/v1/produtos/{self.produto.id}/conversoes/{self.cx.id}/',
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_editar_conversao_sem_dependentes_permitido(self):
        resp = self.client.patch(
            f'/api/v1/produtos/{self.produto.id}/conversoes/{self.cx.id}/',
            {'quantidade_por_base': '12'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.cx.refresh_from_db()
        self.assertEqual(self.cx.quantidade_por_base, Decimal('12'))


class EntradaEstoqueAPICadeiaTest(APITestCase):
    """POST /produtos/{id}/entradas/ com unidade sem conversao (RN-05)."""

    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.produto = _make_produto(unidade_base='UN')

    def test_entrada_unidade_sem_conversao_retorna_400(self):
        resp = self.client.post(
            f'/api/v1/produtos/{self.produto.id}/entradas/',
            {'quantidade': '5', 'unidade': 'KG'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('unidade', resp.data)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_estoque, Decimal('0'))


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


class ComboModelTest(TestCase):
    def setUp(self):
        self.produto1 = _make_produto(nome='Produto 1')
        self.produto2 = _make_produto(nome='Produto 2')

    def test_valor_total_soma_subtotais_dos_itens(self):
        combo = Combo.objects.create(nome='Combo Teste')
        ItemCombo.objects.create(
            combo=combo, produto=self.produto1,
            quantidade=Decimal('2'), valor_unitario=Decimal('10.00'),
        )
        ItemCombo.objects.create(
            combo=combo, produto=self.produto2,
            quantidade=Decimal('3'), valor_unitario=Decimal('5.00'),
        )
        # 2*10 + 3*5 = 35
        self.assertEqual(combo.valor_total, Decimal('35.00'))

    def test_soft_delete_combo(self):
        combo = Combo.objects.create(nome='Combo Teste')
        combo.is_active = False
        combo.save()
        self.assertFalse(Combo.objects.get(pk=combo.pk).is_active)

    def test_produto_nao_pode_ser_excluido_fisicamente_se_usado_em_combo(self):
        combo = Combo.objects.create(nome='Combo Teste')
        ItemCombo.objects.create(
            combo=combo, produto=self.produto1,
            quantidade=Decimal('1'), valor_unitario=Decimal('10.00'),
        )
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.produto1.delete()


class ComboAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.produto1 = _make_produto(nome='Produto 1')
        self.produto2 = _make_produto(nome='Produto 2')

    def test_criar_combo_com_dois_itens(self):
        resp = self.client.post('/api/v1/produtos/combos/', {
            'nome': 'Combo Lanche',
            'descricao': 'Combo de teste',
            'itens': [
                {'produto': self.produto1.id, 'quantidade': '1', 'valor_unitario': '10.00'},
                {'produto': self.produto2.id, 'quantidade': '2', 'valor_unitario': '5.00'},
            ],
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(len(resp.data['itens']), 2)
        self.assertEqual(Decimal(str(resp.data['valor_total'])), Decimal('20.00'))
        combo = Combo.objects.get(pk=resp.data['id'])
        self.assertEqual(combo.criado_por, self.user)

    def test_listar_combos_ativos(self):
        combo = Combo.objects.create(nome='Combo Ativo')
        ItemCombo.objects.create(
            combo=combo, produto=self.produto1,
            quantidade=Decimal('1'), valor_unitario=Decimal('10.00'),
        )
        inativo = Combo.objects.create(nome='Combo Inativo', is_active=False)
        ItemCombo.objects.create(
            combo=inativo, produto=self.produto1,
            quantidade=Decimal('1'), valor_unitario=Decimal('10.00'),
        )
        resp = self.client.get('/api/v1/produtos/combos/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        nomes = [c['nome'] for c in resp.data['results']]
        self.assertIn('Combo Ativo', nomes)
        self.assertNotIn('Combo Inativo', nomes)

    def test_editar_nome_e_itens_do_combo(self):
        combo = Combo.objects.create(nome='Combo Original')
        ItemCombo.objects.create(
            combo=combo, produto=self.produto1,
            quantidade=Decimal('1'), valor_unitario=Decimal('10.00'),
        )
        resp = self.client.patch(f'/api/v1/produtos/combos/{combo.id}/', {
            'nome': 'Combo Renomeado',
            'itens': [
                {'produto': self.produto2.id, 'quantidade': '4', 'valor_unitario': '2.50'},
            ],
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        combo.refresh_from_db()
        self.assertEqual(combo.nome, 'Combo Renomeado')
        self.assertEqual(combo.itens.count(), 1)
        self.assertEqual(combo.itens.first().produto, self.produto2)
        self.assertEqual(combo.valor_total, Decimal('10.00'))

    def test_excluir_combo_soft_delete(self):
        combo = Combo.objects.create(nome='Combo Para Excluir')
        ItemCombo.objects.create(
            combo=combo, produto=self.produto1,
            quantidade=Decimal('1'), valor_unitario=Decimal('10.00'),
        )
        resp = self.client.delete(f'/api/v1/produtos/combos/{combo.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        combo.refresh_from_db()
        self.assertFalse(combo.is_active)

    def test_criar_combo_sem_itens_retorna_400(self):
        resp = self.client.post('/api/v1/produtos/combos/', {
            'nome': 'Combo Vazio',
            'itens': [],
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_criar_combo_com_item_quantidade_zero_retorna_400(self):
        resp = self.client.post('/api/v1/produtos/combos/', {
            'nome': 'Combo Quantidade Zero',
            'itens': [
                {'produto': self.produto1.id, 'quantidade': '0', 'valor_unitario': '10.00'},
            ],
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/produtos/combos/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
