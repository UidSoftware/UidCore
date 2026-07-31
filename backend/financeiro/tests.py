"""Testes do modulo financeiro -- foco na Fase D (conciliacao bancaria automatica).

Cobre RF-D01 a RF-D11 e RN-D01 a RN-D07 da Especificacao_Hotfix.md (Manutencao #7).
"""
import os
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from . import parsers
from .conciliacao_service import auto_processar, criar_conciliacao, executar_matching
from .models import (
    Aporte, Categoria, Conta, ConciliacaoExtrato, Despesa,
    ItemConciliacao, LivroCaixa, PadraoSeguroConciliacao, Receita,
)


def _make_user(email='admin@teste.com'):
    return User.objects.create_user(email=email, password='senha123', nome_completo='Admin Teste')


def _make_conta(nome='Conta C6 PJ', saldo_inicial=Decimal('0')):
    return Conta.objects.create(nome=nome, tipo='CORRENTE', saldo_inicial=saldo_inicial)


# --- RF-D02 a RF-D04: parsers.py -----------------------------------------

class ParsersTest(TestCase):
    def test_parse_c6_entrada_e_saida(self):
        texto = (
            '01/07  PIX RECEBIDO JOAO SILVA  +1.500,00\n'
            '02/07  PAGAMENTO FORNECEDOR XYZ  -320,50\n'
        )
        resultado = parsers.parse_c6(texto, ano=2026)
        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0]['tipo'], 'ENTRADA')
        self.assertEqual(resultado[0]['valor'], Decimal('1500.00'))
        self.assertEqual(resultado[0]['data'], date(2026, 7, 1))
        self.assertEqual(resultado[1]['tipo'], 'SAIDA')
        self.assertEqual(resultado[1]['valor'], Decimal('320.50'))

    def test_parse_c6_ignora_valor_zero(self):
        texto = '03/07  AJUSTE SEM VALOR  +0,00\n'
        resultado = parsers.parse_c6(texto, ano=2026)
        self.assertEqual(resultado, [])

    def test_parse_btg_debito_e_credito(self):
        texto = (
            '01/07/2026  TED RECEBIDA  C  2.000,00\n'
            '02/07/2026  BOLETO PAGO  D  450,00\n'
        )
        resultado = parsers.parse_btg(texto, ano=2026)
        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0]['tipo'], 'ENTRADA')
        self.assertEqual(resultado[0]['valor'], Decimal('2000.00'))
        self.assertEqual(resultado[1]['tipo'], 'SAIDA')

    def test_stubs_retornam_lista_vazia(self):
        for func in (parsers.parse_nubank, parsers.parse_inter, parsers.parse_caixa, parsers.parse_itau):
            self.assertEqual(func('qualquer texto', ano=2026), [])

    def test_get_parser_por_substring_case_insensitive(self):
        self.assertIs(parsers.get_parser('Conta c6 PJ'), parsers.parse_c6)
        self.assertIs(parsers.get_parser('BTG Investimentos'), parsers.parse_btg)
        self.assertIs(parsers.get_parser('nubank conta'), parsers.parse_nubank)

    def test_get_parser_sem_match_levanta_value_error(self):
        with self.assertRaises(ValueError):
            parsers.get_parser('Banco Desconhecido')

    def test_parse_valor_br(self):
        self.assertEqual(parsers._parse_valor_br('1.234,56'), Decimal('1234.56'))
        self.assertEqual(parsers._parse_valor_br('lixo'), Decimal('0'))


class PdfSenhaTest(TestCase):
    """RN-D07 -- PDF protegido por senha sem o campo senha deve ser rejeitado."""

    def _criar_pdf_protegido(self, path, senha_usuario):
        import pikepdf
        pdf = pikepdf.new()
        pdf.add_blank_page(page_size=(200, 200))
        pdf.save(path, encryption=pikepdf.Encryption(owner='dono-teste', user=senha_usuario))

    def test_pdf_com_senha_sem_informar_senha_levanta_erro(self):
        path = '/tmp/uidcore_teste_protegido_1.pdf'
        self._criar_pdf_protegido(path, 'segredo123')
        try:
            with self.assertRaises(RuntimeError):
                parsers.extrair_texto_pdf(path, senha=None)
        finally:
            os.remove(path)

    def test_pdf_com_senha_correta_extrai_normalmente(self):
        path = '/tmp/uidcore_teste_protegido_2.pdf'
        self._criar_pdf_protegido(path, 'segredo123')
        try:
            texto = parsers.extrair_texto_pdf(path, senha='segredo123')
            self.assertIsInstance(texto, str)
        finally:
            os.remove(path)


# --- RF-D05 / RF-D06: matching + ambiguidade (financeiro/conciliacao_service.py) ---

class ExecutarMatchingTest(TestCase):
    def setUp(self):
        self.conta = _make_conta()

    def test_camada_1_concilia_por_data_valor_tipo(self):
        LivroCaixa.objects.create(
            conta=self.conta, tipo='ENTRADA', origem='MANUAL', descricao='Recebimento',
            valor=Decimal('150.00'), data=date(2026, 7, 5),
            saldo_anterior=Decimal('0'), saldo_atual=Decimal('150.00'),
        )
        transacoes_banco = [{
            'data': date(2026, 7, 5), 'descricao': 'PIX RECEBIDO',
            'valor': Decimal('150.00'), 'tipo': 'ENTRADA',
        }]
        itens, lancamentos_sistema = executar_matching(self.conta, transacoes_banco, date(2026, 7, 1))
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]['status'], 'CONCILIADO')

    def test_lancamento_sem_transacao_correspondente_fica_faltando_banco(self):
        LivroCaixa.objects.create(
            conta=self.conta, tipo='SAIDA', origem='MANUAL', descricao='Pagamento nao no extrato',
            valor=Decimal('80.00'), data=date(2026, 7, 8),
            saldo_anterior=Decimal('0'), saldo_atual=Decimal('-80.00'),
        )
        itens, _ = executar_matching(self.conta, [], date(2026, 7, 1))
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]['status'], 'FALTANDO_BANCO')

    def test_estornado_ignorado_no_matching_rn_d02(self):
        LivroCaixa.objects.create(
            conta=self.conta, tipo='ENTRADA', origem='MANUAL', descricao='Lancamento estornado',
            valor=Decimal('100.00'), data=date(2026, 7, 5),
            saldo_anterior=Decimal('0'), saldo_atual=Decimal('100.00'), estornado=True,
        )
        transacoes_banco = [{
            'data': date(2026, 7, 5), 'descricao': 'PIX', 'valor': Decimal('100.00'), 'tipo': 'ENTRADA',
        }]
        itens, lancamentos_sistema = executar_matching(self.conta, transacoes_banco, date(2026, 7, 1))
        self.assertEqual(lancamentos_sistema, [])
        self.assertEqual(itens[0]['status'], 'FALTANDO_SISTEMA')

    def test_livrocaixa_ja_conciliado_nao_e_reutilizado_rn_d01(self):
        lc = LivroCaixa.objects.create(
            conta=self.conta, tipo='ENTRADA', origem='MANUAL', descricao='Recebimento',
            valor=Decimal('150.00'), data=date(2026, 7, 5),
            saldo_anterior=Decimal('0'), saldo_atual=Decimal('150.00'),
        )
        conc_anterior = ConciliacaoExtrato.objects.create(
            conta=self.conta, arquivo_nome='extrato_antigo.pdf', periodo=date(2026, 7, 1),
            status='PROCESSADO', total_banco=Decimal('150.00'), total_sistema=Decimal('150.00'),
        )
        ItemConciliacao.objects.create(
            conciliacao=conc_anterior, data_banco=date(2026, 7, 5), descricao_banco='PIX',
            valor=Decimal('150.00'), tipo='ENTRADA', status='CONCILIADO', lancamento_lc=lc,
        )

        # Re-upload do mesmo extrato (usuario enviou o mesmo PDF de novo)
        transacoes_banco = [{
            'data': date(2026, 7, 5), 'descricao': 'PIX', 'valor': Decimal('150.00'), 'tipo': 'ENTRADA',
        }]
        itens, lancamentos_sistema = executar_matching(self.conta, transacoes_banco, date(2026, 7, 1))
        self.assertEqual(lancamentos_sistema, [])  # lc ja conciliado nao entra no pool de matching
        self.assertEqual(itens[0]['status'], 'FALTANDO_SISTEMA')


class AmbiguidadeAutoProcessarTest(TestCase):
    """RF-D06 -- ambiguidade NUNCA decide automaticamente (BUG 1 corrigido)."""

    def setUp(self):
        self.conta = _make_conta()
        self.categoria = Categoria.objects.create(nome='Servicos', tipo='ENTRADA')

    def _criar_item_pendente(self, data_banco, valor, tipo, descricao='PIX RECEBIDO CLIENTE'):
        conc = ConciliacaoExtrato.objects.create(
            conta=self.conta, arquivo_nome='extrato.pdf', periodo=date(2026, 7, 1),
            status='COM_DIVERGENCIAS', total_banco=valor, total_sistema=Decimal('0'), divergencias=1,
        )
        item_conc = ItemConciliacao.objects.create(
            conciliacao=conc, data_banco=data_banco, descricao_banco=descricao,
            valor=valor, tipo=tipo, status='FALTANDO_SISTEMA',
        )
        item_dict = {
            'data_banco': data_banco, 'descricao_banco': descricao, 'valor': valor, 'tipo': tipo,
        }
        return conc, item_conc, item_dict

    def test_duas_receitas_pendentes_mesmo_valor_e_janela_nao_assenta_nenhuma(self):
        """Cenario central do BUG 1: 2 Receitas PENDENTE com mesmo valor_liquido e
        vencimento dentro de +-3 dias do item do extrato -- nenhuma pode ser
        assentada automaticamente, e o item deve continuar FALTANDO_SISTEMA."""
        vencimento_base = date(2026, 7, 10)
        receita_a = Receita.objects.create(
            conta=self.conta, tipo='SERVICO', descricao='Receita A',
            categoria=self.categoria, valor_bruto=Decimal('500.00'),
            vencimento=vencimento_base, status='PENDENTE',
        )
        receita_b = Receita.objects.create(
            conta=self.conta, tipo='SERVICO', descricao='Receita B',
            categoria=self.categoria, valor_bruto=Decimal('500.00'),
            vencimento=vencimento_base + timedelta(days=2), status='PENDENTE',
        )

        conc, item_conc, item_dict = self._criar_item_pendente(
            vencimento_base, Decimal('500.00'), 'ENTRADA',
        )

        resultado = auto_processar([item_dict], self.conta, conc)

        receita_a.refresh_from_db()
        receita_b.refresh_from_db()
        item_conc.refresh_from_db()

        self.assertEqual(receita_a.status, 'PENDENTE', 'Receita A NAO deveria ter sido assentada automaticamente')
        self.assertEqual(receita_b.status, 'PENDENTE', 'Receita B NAO deveria ter sido assentada automaticamente')
        self.assertEqual(item_conc.status, 'FALTANDO_SISTEMA')
        self.assertFalse(item_conc.confirmado)
        self.assertEqual(LivroCaixa.objects.filter(conta=self.conta, origem='RECEITA').count(), 0)
        self.assertEqual(resultado['assentados'], 0)

    def test_duas_despesas_pendentes_mesmo_valor_e_janela_nao_assenta_nenhuma(self):
        vencimento_base = date(2026, 7, 12)
        despesa_a = Despesa.objects.create(
            conta=self.conta, tipo='VARIAVEL', descricao='Despesa A',
            valor_bruto=Decimal('220.00'), vencimento=vencimento_base, status='PENDENTE',
        )
        despesa_b = Despesa.objects.create(
            conta=self.conta, tipo='VARIAVEL', descricao='Despesa B',
            valor_bruto=Decimal('220.00'), vencimento=vencimento_base - timedelta(days=1), status='ATRASADO',
        )

        conc, item_conc, item_dict = self._criar_item_pendente(
            vencimento_base, Decimal('220.00'), 'SAIDA', descricao='PAGAMENTO FORNECEDOR',
        )

        auto_processar([item_dict], self.conta, conc)

        despesa_a.refresh_from_db()
        despesa_b.refresh_from_db()
        item_conc.refresh_from_db()

        self.assertEqual(despesa_a.status, 'PENDENTE')
        self.assertEqual(despesa_b.status, 'ATRASADO')
        self.assertEqual(item_conc.status, 'FALTANDO_SISTEMA')
        self.assertEqual(LivroCaixa.objects.filter(conta=self.conta, origem='DESPESA').count(), 0)

    def test_uma_unica_receita_candidata_e_assentada_automaticamente(self):
        vencimento = date(2026, 7, 10)
        receita = Receita.objects.create(
            conta=self.conta, tipo='SERVICO', descricao='Receita Unica',
            categoria=self.categoria, valor_bruto=Decimal('300.00'),
            vencimento=vencimento, status='PENDENTE',
        )
        conc, item_conc, item_dict = self._criar_item_pendente(vencimento, Decimal('300.00'), 'ENTRADA')

        resultado = auto_processar([item_dict], self.conta, conc)

        receita.refresh_from_db()
        item_conc.refresh_from_db()
        self.assertEqual(receita.status, 'RECEBIDO')
        self.assertEqual(item_conc.status, 'CONCILIADO')
        self.assertTrue(item_conc.confirmado)
        self.assertIsNotNone(item_conc.lancamento_lc)
        self.assertEqual(resultado['assentados'], 1)

    def test_dois_padroes_ativos_ambiguos_nao_cria_nada(self):
        PadraoSeguroConciliacao.objects.create(
            descricao_padrao='RENDIMENTO', tipo='ENTRADA', natureza='RECEITA_FINANCEIRA',
        )
        PadraoSeguroConciliacao.objects.create(
            descricao_padrao='RENDIMENTO CDB', tipo='ENTRADA', natureza='APORTE',
        )
        conc, item_conc, item_dict = self._criar_item_pendente(
            date(2026, 7, 15), Decimal('42.10'), 'ENTRADA', descricao='RENDIMENTO CDB JULHO',
        )

        resultado = auto_processar([item_dict], self.conta, conc)

        item_conc.refresh_from_db()
        self.assertEqual(item_conc.status, 'FALTANDO_SISTEMA')
        self.assertFalse(item_conc.confirmado)
        self.assertEqual(Receita.objects.filter(conta=self.conta).count(), 0)
        self.assertEqual(Aporte.objects.filter(conta=self.conta).count(), 0)
        self.assertEqual(resultado['criados_padrao'], 0)

    def test_padrao_unico_cria_aporte_rn_d06(self):
        PadraoSeguroConciliacao.objects.create(
            descricao_padrao='APORTE SOCIO', tipo='ENTRADA', natureza='APORTE',
        )
        conc, item_conc, item_dict = self._criar_item_pendente(
            date(2026, 7, 20), Decimal('1000.00'), 'ENTRADA', descricao='APORTE SOCIO LUIZ',
        )

        resultado = auto_processar([item_dict], self.conta, conc)

        self.assertEqual(resultado['criados_padrao'], 1)
        aporte = Aporte.objects.get(conta=self.conta)
        self.assertEqual(aporte.valor, Decimal('1000.00'))
        item_conc.refresh_from_db()
        self.assertTrue(item_conc.confirmado)

    def test_padrao_receita_financeira_entra_no_dre_rn_d06(self):
        PadraoSeguroConciliacao.objects.create(
            descricao_padrao='JUROS APLICACAO', tipo='ENTRADA', natureza='RECEITA_FINANCEIRA',
        )
        conc, item_conc, item_dict = self._criar_item_pendente(
            date(2026, 7, 22), Decimal('15.30'), 'ENTRADA', descricao='JUROS APLICACAO CDB',
        )

        auto_processar([item_dict], self.conta, conc)

        receita = Receita.objects.get(conta=self.conta)
        self.assertEqual(receita.tipo, 'RECEITA_FINANCEIRA')
        self.assertEqual(receita.status, 'RECEBIDO')

    def test_sem_padrao_e_sem_pendente_fica_aguardando_revisao(self):
        conc, item_conc, item_dict = self._criar_item_pendente(
            date(2026, 7, 25), Decimal('99.99'), 'SAIDA', descricao='COMPRA DESCONHECIDA',
        )

        resultado = auto_processar([item_dict], self.conta, conc)

        item_conc.refresh_from_db()
        self.assertEqual(item_conc.status, 'FALTANDO_SISTEMA')
        self.assertEqual(resultado['aguardando_revisao'], 1)
        self.assertEqual(resultado['assentados'], 0)
        self.assertEqual(resultado['criados_padrao'], 0)


class CriarConciliacaoTest(TestCase):
    def setUp(self):
        self.conta = _make_conta()

    def test_periodo_e_primeiro_dia_do_mes_rn_d04(self):
        conc = criar_conciliacao(
            conta=self.conta, transacoes_banco=[], periodo=date(2026, 7, 1),
            arquivo_nome='extrato_julho.pdf',
        )
        self.assertEqual(conc.periodo, date(2026, 7, 1))

    def test_arquivo_nome_armazena_apenas_nome_rn_d03(self):
        conc = criar_conciliacao(
            conta=self.conta, transacoes_banco=[], periodo=date(2026, 7, 1),
            arquivo_nome='extrato_julho.pdf',
        )
        self.assertEqual(conc.arquivo_nome, 'extrato_julho.pdf')
        self.assertNotIn('/', conc.arquivo_nome)

    def test_sem_transacoes_e_sem_pendencias_status_processado_rn_d05(self):
        conc = criar_conciliacao(
            conta=self.conta, transacoes_banco=[], periodo=date(2026, 7, 1),
            arquivo_nome='extrato.pdf',
        )
        self.assertEqual(conc.status, 'PROCESSADO')
        self.assertEqual(conc.divergencias, 0)

    def test_com_pendencia_status_com_divergencias_rn_d05(self):
        conc = criar_conciliacao(
            conta=self.conta,
            transacoes_banco=[{
                'data': date(2026, 7, 5), 'descricao': 'PIX nao reconhecido',
                'valor': Decimal('80.00'), 'tipo': 'ENTRADA',
            }],
            periodo=date(2026, 7, 1), arquivo_nome='extrato.pdf',
        )
        self.assertEqual(conc.status, 'COM_DIVERGENCIAS')
        self.assertEqual(conc.divergencias, 1)

    def test_transaction_atomic_persiste_conc_e_itens_juntos_rf_d07(self):
        conc = criar_conciliacao(
            conta=self.conta,
            transacoes_banco=[{
                'data': date(2026, 7, 5), 'descricao': 'PIX', 'valor': Decimal('10.00'), 'tipo': 'ENTRADA',
            }],
            periodo=date(2026, 7, 1), arquivo_nome='extrato.pdf',
        )
        self.assertEqual(ConciliacaoExtrato.objects.filter(pk=conc.pk).count(), 1)
        self.assertEqual(ItemConciliacao.objects.filter(conciliacao=conc).count(), 1)


# --- RF-D08 a RF-D11: endpoints (financeiro/views.py) ---------------------

class ConciliacaoListagemAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.conta = _make_conta()
        self.conc = criar_conciliacao(
            conta=self.conta,
            transacoes_banco=[{
                'data': date(2026, 7, 5), 'descricao': 'PIX nao reconhecido',
                'valor': Decimal('80.00'), 'tipo': 'ENTRADA',
            }],
            periodo=date(2026, 7, 1), arquivo_nome='extrato.pdf',
        )

    def test_listar_conciliacoes_rf_d08(self):
        resp = self.client.get('/api/v1/financeiro/conciliacoes/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data['results']), 1)
        self.assertIn('conta_nome', resp.data['results'][0])

    def test_listar_itens_da_conciliacao_rf_d09(self):
        url = f'/api/v1/financeiro/conciliacoes/{self.conc.id}/itens/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_confirmar_item_atualiza_divergencias_rf_d10(self):
        item = self.conc.itens.first()
        url = f'/api/v1/financeiro/conciliacoes/{self.conc.id}/confirmar-item/'
        resp = self.client.post(url, {'item_id': item.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['divergencias_restantes'], 0)
        self.conc.refresh_from_db()
        self.assertEqual(self.conc.status, 'PROCESSADO')

    def test_confirmar_item_sem_item_id_400(self):
        url = f'/api/v1/financeiro/conciliacoes/{self.conc.id}/confirmar-item/'
        resp = self.client.post(url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_listar_conciliacoes_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/financeiro/conciliacoes/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class PadraoSeguroConciliacaoAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)

    def test_crud_padroes_rf_d11(self):
        url = '/api/v1/financeiro/padroes-conciliacao/'
        resp = self.client.post(url, {
            'descricao_padrao': 'JUROS APLICACAO', 'tipo': 'ENTRADA', 'natureza': 'RECEITA_FINANCEIRA',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        padrao_id = resp.data['id']

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)

        resp = self.client.delete(f'{url}{padrao_id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        padrao = PadraoSeguroConciliacao.objects.get(pk=padrao_id)
        self.assertFalse(padrao.is_active)  # soft delete via is_active (herda BaseModel)

        # Apos "destroy" o padrao nao aparece mais na listagem (queryset filtra is_active=True)
        resp = self.client.get(url)
        self.assertEqual(len(resp.data['results']), 0)


# --- RF-D01: endpoint de upload (financeiro/views.py) ---------------------

class ConciliacaoUploadAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.conta = _make_conta(nome='Conta C6 PJ')

    @patch('financeiro.views.get_parser')
    @patch('financeiro.views.extrair_texto_pdf')
    def test_upload_cria_conciliacao_rf_d01(self, mock_extrair, mock_get_parser):
        mock_extrair.return_value = 'texto fake'
        mock_get_parser.return_value = lambda texto, ano: [
            {'data': date(2026, 7, 5), 'descricao': 'PIX TESTE', 'valor': Decimal('50.00'), 'tipo': 'ENTRADA'},
        ]
        arquivo = SimpleUploadedFile('extrato_2026-07.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        resp = self.client.post('/api/v1/financeiro/conciliacoes/upload/', {
            'arquivo': arquivo, 'conta_id': self.conta.id, 'periodo': '2026-07', 'auto': 'false',
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['arquivo_nome'], 'extrato_2026-07.pdf')
        conc = ConciliacaoExtrato.objects.get(pk=resp.data['id'])
        self.assertEqual(conc.itens.count(), 1)

    @patch('financeiro.views.get_parser')
    @patch('financeiro.views.extrair_texto_pdf')
    def test_upload_auto_flag_dispara_auto_processar_bug2_corrigido(self, mock_extrair, mock_get_parser):
        """BUG 2 corrigido: o parametro `auto` do endpoint upload/ era morto (a Camada
        2/3 nunca era chamada). Agora precisa efetivamente criar o lancamento via
        PadraoSeguroConciliacao quando auto=true."""
        PadraoSeguroConciliacao.objects.create(
            descricao_padrao='APORTE SOCIO', tipo='ENTRADA', natureza='APORTE',
        )
        mock_extrair.return_value = 'texto fake'
        mock_get_parser.return_value = lambda texto, ano: [
            {'data': date(2026, 7, 8), 'descricao': 'APORTE SOCIO LUIZ', 'valor': Decimal('900.00'), 'tipo': 'ENTRADA'},
        ]
        arquivo = SimpleUploadedFile('extrato_2026-07.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        resp = self.client.post('/api/v1/financeiro/conciliacoes/upload/', {
            'arquivo': arquivo, 'conta_id': self.conta.id, 'periodo': '2026-07', 'auto': 'true',
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Aporte.objects.filter(conta=self.conta).count(), 1)
        conc = ConciliacaoExtrato.objects.get(pk=resp.data['id'])
        item = conc.itens.first()
        self.assertTrue(item.confirmado)

    @patch('financeiro.views.get_parser')
    @patch('financeiro.views.extrair_texto_pdf')
    def test_upload_sem_auto_flag_nao_processa_camada_2_3(self, mock_extrair, mock_get_parser):
        PadraoSeguroConciliacao.objects.create(
            descricao_padrao='APORTE SOCIO', tipo='ENTRADA', natureza='APORTE',
        )
        mock_extrair.return_value = 'texto fake'
        mock_get_parser.return_value = lambda texto, ano: [
            {'data': date(2026, 7, 8), 'descricao': 'APORTE SOCIO LUIZ', 'valor': Decimal('900.00'), 'tipo': 'ENTRADA'},
        ]
        arquivo = SimpleUploadedFile('extrato_2026-07.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        resp = self.client.post('/api/v1/financeiro/conciliacoes/upload/', {
            'arquivo': arquivo, 'conta_id': self.conta.id, 'periodo': '2026-07',
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Aporte.objects.filter(conta=self.conta).count(), 0)

    def test_upload_conta_inexistente_404(self):
        arquivo = SimpleUploadedFile('extrato.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        resp = self.client.post('/api/v1/financeiro/conciliacoes/upload/', {
            'arquivo': arquivo, 'conta_id': 999999, 'periodo': '2026-07',
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_upload_periodo_invalido_400(self):
        arquivo = SimpleUploadedFile('extrato.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        resp = self.client.post('/api/v1/financeiro/conciliacoes/upload/', {
            'arquivo': arquivo, 'conta_id': self.conta.id, 'periodo': 'invalido',
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_campos_obrigatorios_400(self):
        resp = self.client.post('/api/v1/financeiro/conciliacoes/upload/', {}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# --- Fase D (Manutenção #11): dashboard com despesas/receitas por mes -----

class DashboardFinanceiroPorMesTest(APITestCase):
    """Fase D: verifica que dashboard retorna despesas_pagas_por_mes e
    receitas_recebidas_por_mes com a estrutura correta."""

    def setUp(self):
        from datetime import date
        self.user = _make_user(email='dash@teste.com')
        self.client.force_authenticate(self.user)
        self.conta = _make_conta(nome='Conta Dashboard Teste')
        self.categoria = Categoria.objects.create(nome='Servico', tipo='ENTRADA')

        hoje = date.today()

        # Criar despesa paga no mes atual
        Despesa.objects.create(
            conta=self.conta, tipo='FIXA', descricao='Aluguel Dash',
            valor_bruto=Decimal('1000.00'), pagamento=hoje, status='PAGO',
        )
        # Criar receita recebida no mes atual
        Receita.objects.create(
            conta=self.conta, tipo='SERVICO', descricao='Receita Dash',
            categoria=self.categoria,
            valor_bruto=Decimal('2000.00'), recebimento=hoje, status='RECEBIDO',
        )

    def test_dashboard_inclui_campos_novos(self):
        resp = self.client.get('/api/v1/financeiro/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('despesas_pagas_por_mes', resp.data)
        self.assertIn('receitas_recebidas_por_mes', resp.data)

    def test_despesas_pagas_por_mes_estrutura(self):
        resp = self.client.get('/api/v1/financeiro/dashboard/')
        desp_list = resp.data['despesas_pagas_por_mes']
        self.assertIsInstance(desp_list, list)
        self.assertGreaterEqual(len(desp_list), 1)
        primeiro = desp_list[-1]  # mes mais recente deve estar no final
        self.assertIn('mes', primeiro)
        self.assertIn('label', primeiro)
        self.assertIn('total', primeiro)
        self.assertIn('itens', primeiro)

    def test_receitas_recebidas_por_mes_estrutura(self):
        resp = self.client.get('/api/v1/financeiro/dashboard/')
        rec_list = resp.data['receitas_recebidas_por_mes']
        self.assertIsInstance(rec_list, list)
        self.assertGreaterEqual(len(rec_list), 1)
        primeiro = rec_list[-1]
        self.assertIn('mes', primeiro)
        self.assertIn('label', primeiro)
        self.assertIn('total', primeiro)
        self.assertIn('itens', primeiro)

    def test_itens_tem_campos_corretos(self):
        resp = self.client.get('/api/v1/financeiro/dashboard/')
        desp_list = resp.data['despesas_pagas_por_mes']
        if desp_list:
            item = desp_list[-1]['itens'][0]
            self.assertIn('id', item)
            self.assertIn('descricao', item)
            self.assertIn('valor', item)
            self.assertIn('data', item)

    def test_despesa_pendente_nao_aparece(self):
        from datetime import date
        Despesa.objects.create(
            conta=self.conta, tipo='FIXA', descricao='Pendente NAO Aparece',
            valor_bruto=Decimal('500.00'), status='PENDENTE',
        )
        resp = self.client.get('/api/v1/financeiro/dashboard/')
        todas_descricoes = []
        for mes in resp.data['despesas_pagas_por_mes']:
            todas_descricoes.extend([i['descricao'] for i in mes['itens']])
        self.assertNotIn('Pendente NAO Aparece', todas_descricoes)

    def test_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/financeiro/dashboard/')
        self.assertEqual(resp.status_code, 401)
