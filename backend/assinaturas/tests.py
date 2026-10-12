"""
Testes do app assinaturas — Manutencao #64 [NUCLEO 3/5].

Cobre RF-01 a RF-07 e RN-01 a RN-10 da Especificacao_Hotfix.md, ponta a
ponta via API real quando possivel (JWT real via force_authenticate) e via
chamada direta do service/command onde a Especificacao explicita isso
(ex: CA-04 dry-run, CA-08 erro parcial no lote).

CA-07 (test_ca07_...) e o teste que materializa a licao real do NosFluir
(Studio Fluir): data_fim no passado bloqueia geracao mesmo que o status
ainda nao tenha sido movido para ENCERRADA manualmente.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.management import call_command
from django.db.utils import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from clientes.models import Cliente
from financeiro.models import Categoria, Conta, Receita, StatusReceita, TipoReceita

from .models import Assinatura, Periodicidade, Plano, StatusAssinatura
from .services import gerar_cobrancas_mes


def _make_user(email='admin@teste.com', is_staff=True, perfil='ADMIN'):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Admin Teste',
        is_staff=is_staff, perfil=perfil,
    )


def _make_cliente(nome='Cliente Teste'):
    return Cliente.objects.create(nome_razao_social=nome, tipo_pessoa='PF')


def _make_conta(nome='Conta Teste'):
    return Conta.objects.create(nome=nome, tipo='CORRENTE', saldo_inicial=Decimal('0'))


def _make_categoria():
    categoria, _ = Categoria.objects.get_or_create(nome='Mensalidade Assinatura', tipo='ENTRADA')
    return categoria


def _make_plano(periodicidade=Periodicidade.MENSAL, valor=Decimal('100.00')):
    return Plano.objects.create(
        nome=f'Plano {periodicidade}', valor=valor,
        periodicidade=periodicidade, categoria=_make_categoria(),
    )


def _make_assinatura(cliente=None, plano=None, conta=None, data_inicio=date(2026, 1, 15),
                      data_fim=None, status_=StatusAssinatura.ATIVA, dia_vencimento=10,
                      valor=None):
    plano = plano or _make_plano()
    return Assinatura.objects.create(
        cliente=cliente or _make_cliente(),
        plano=plano,
        valor=valor if valor is not None else plano.valor,
        dia_vencimento=dia_vencimento,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=status_,
        conta=conta or _make_conta(),
    )


class PlanoModelTest(TestCase):
    def test_str(self):
        plano = _make_plano()
        self.assertIn('Plano', str(plano))

    def test_ativo_default_true_distinto_de_is_active(self):
        plano = _make_plano()
        self.assertTrue(plano.ativo)
        self.assertTrue(plano.is_active)
        plano.ativo = False
        plano.save()
        plano.refresh_from_db()
        self.assertFalse(plano.ativo)
        self.assertTrue(plano.is_active)  # RF-02: nao e soft delete


class AssinaturaModelTest(TestCase):
    def test_status_default_ativa(self):
        assinatura = _make_assinatura()
        self.assertEqual(assinatura.status, StatusAssinatura.ATIVA)

    def test_valor_snapshot_nao_segue_plano(self):
        plano = _make_plano(valor=Decimal('50.00'))
        assinatura = _make_assinatura(plano=plano)
        plano.valor = Decimal('999.00')
        plano.save()
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.valor, Decimal('50.00'))  # RF-03: snapshot


class GerarCobrancasMesServiceTest(TestCase):
    """RF-05 / RN-01 a RN-06, RN-08, RN-09 — testes diretos do service,
    mais granulares do que via API/command."""

    def test_ca01_gera_uma_receita_pendente_mes_correto(self):
        assinatura = _make_assinatura(data_inicio=date(2026, 10, 1))
        mes = date(2026, 11, 1)

        resumo = gerar_cobrancas_mes(mes)

        self.assertEqual(resumo['criadas'], 1)
        receita = Receita.objects.get(assinatura=assinatura, referencia_mes=mes)
        self.assertEqual(receita.status, StatusReceita.PENDENTE)
        self.assertEqual(receita.tipo, TipoReceita.MENSALIDADE)
        self.assertEqual(receita.valor_bruto, assinatura.valor)
        self.assertEqual(receita.cliente_id, assinatura.cliente_id)
        self.assertEqual(receita.conta_id, assinatura.conta_id)
        self.assertEqual(receita.vencimento, date(2026, 11, 10))

    def test_ca02_rodar_2x_mesmo_mes_nao_duplica(self):
        _make_assinatura(data_inicio=date(2026, 10, 1))
        mes = date(2026, 11, 1)

        resumo1 = gerar_cobrancas_mes(mes)
        resumo2 = gerar_cobrancas_mes(mes)

        self.assertEqual(resumo1['criadas'], 1)
        self.assertEqual(resumo2['criadas'], 0)
        self.assertEqual(resumo2['puladas_idempotencia'], 1)
        self.assertEqual(Receita.objects.filter(referencia_mes=mes).count(), 1)

    def test_ca03_encerrar_assinatura_nao_gera_mes_seguinte(self):
        assinatura = _make_assinatura(data_inicio=date(2026, 9, 1))
        gerar_cobrancas_mes(date(2026, 10, 1))

        assinatura.status = StatusAssinatura.ENCERRADA
        assinatura.data_fim = date(2026, 10, 15)
        assinatura.save()

        resumo = gerar_cobrancas_mes(date(2026, 11, 1))
        self.assertEqual(resumo['criadas'], 0)
        self.assertFalse(Receita.objects.filter(assinatura=assinatura, referencia_mes=date(2026, 11, 1)).exists())

    def test_ca04_dry_run_nao_persiste_nada(self):
        _make_assinatura(data_inicio=date(2026, 10, 1))
        mes = date(2026, 11, 1)

        resumo = gerar_cobrancas_mes(mes, dry_run=True)

        self.assertEqual(resumo['criadas'], 1)  # contabiliza o que SERIA criado
        self.assertEqual(Receita.objects.count(), 0)  # mas nao grava nada (RN-08)

    def test_ca05_pausada_nunca_gera(self):
        assinatura = _make_assinatura(data_inicio=date(2026, 1, 1), status_=StatusAssinatura.PAUSADA)

        resumo_nov = gerar_cobrancas_mes(date(2026, 11, 1))
        resumo_dez = gerar_cobrancas_mes(date(2026, 12, 1))

        self.assertEqual(resumo_nov['criadas'], 0)
        self.assertEqual(resumo_dez['criadas'], 0)
        self.assertFalse(Receita.objects.filter(assinatura=assinatura).exists())

    def test_ca06_trimestral_gera_so_nos_meses_de_competencia(self):
        plano = _make_plano(periodicidade=Periodicidade.TRIMESTRAL)
        assinatura = _make_assinatura(plano=plano, data_inicio=date(2026, 1, 15))

        meses_que_geram = [date(2026, 1, 1), date(2026, 4, 1), date(2026, 7, 1), date(2026, 10, 1)]
        meses_que_nao_geram = [date(2026, 2, 1), date(2026, 3, 1), date(2026, 5, 1), date(2026, 6, 1)]

        for mes in meses_que_geram:
            resumo = gerar_cobrancas_mes(mes)
            self.assertEqual(resumo['criadas'], 1, f'deveria gerar em {mes}')

        for mes in meses_que_nao_geram:
            resumo = gerar_cobrancas_mes(mes)
            self.assertEqual(resumo['criadas'], 0, f'nao deveria gerar em {mes}')
            self.assertEqual(resumo['puladas_elegibilidade'], 1)

        self.assertEqual(Receita.objects.filter(assinatura=assinatura).count(), 4)

    def test_ca06_semestral_gera_so_nos_meses_de_competencia(self):
        plano = _make_plano(periodicidade=Periodicidade.SEMESTRAL)
        assinatura = _make_assinatura(plano=plano, data_inicio=date(2026, 2, 1))

        for mes in [date(2026, 2, 1), date(2026, 8, 1)]:
            self.assertEqual(gerar_cobrancas_mes(mes)['criadas'], 1)
        for mes in [date(2026, 3, 1), date(2026, 5, 1), date(2026, 7, 1)]:
            self.assertEqual(gerar_cobrancas_mes(mes)['criadas'], 0)

        self.assertEqual(Receita.objects.filter(assinatura=assinatura).count(), 2)

    def test_ca06_anual_gera_so_nos_meses_de_competencia(self):
        plano = _make_plano(periodicidade=Periodicidade.ANUAL)
        assinatura = _make_assinatura(plano=plano, data_inicio=date(2025, 6, 1))

        for mes in [date(2025, 6, 1), date(2026, 6, 1)]:
            self.assertEqual(gerar_cobrancas_mes(mes)['criadas'], 1)
        for mes in [date(2025, 12, 1), date(2026, 1, 1), date(2026, 5, 1)]:
            self.assertEqual(gerar_cobrancas_mes(mes)['criadas'], 0)

        self.assertEqual(Receita.objects.filter(assinatura=assinatura).count(), 2)

    def test_ca07_data_fim_no_passado_bloqueia_mesmo_status_ainda_ativa(self):
        """
        RN-03/RN-04 — a licao real do NosFluir: a assinatura segue com
        status=ATIVA (ninguem chamou a action encerrar), mas data_fim ja
        passou. Mesmo assim NAO pode gerar cobranca do mes seguinte --
        isso tem que estar garantido pela query de elegibilidade, nao por
        confiar que o status sempre foi movido corretamente.
        """
        assinatura = _make_assinatura(
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 8, 31),
            status_=StatusAssinatura.ATIVA,  # status NAO movido para ENCERRADA de proposito
        )

        resumo = gerar_cobrancas_mes(date(2026, 9, 1))

        self.assertEqual(resumo['criadas'], 0)
        self.assertFalse(Receita.objects.filter(assinatura=assinatura, referencia_mes=date(2026, 9, 1)).exists())

    def test_data_inicio_no_futuro_nao_gera(self):
        assinatura = _make_assinatura(data_inicio=date(2027, 1, 1))
        resumo = gerar_cobrancas_mes(date(2026, 12, 1))
        self.assertEqual(resumo['criadas'], 0)
        self.assertFalse(Receita.objects.filter(assinatura=assinatura).exists())

    def test_ca08_erro_em_uma_assinatura_nao_impede_as_demais(self):
        ass_ok1 = _make_assinatura(data_inicio=date(2026, 1, 1))
        ass_erro = _make_assinatura(data_inicio=date(2026, 1, 1))
        ass_ok2 = _make_assinatura(data_inicio=date(2026, 1, 1))

        original_get_or_create = Receita.objects.get_or_create

        def fake_get_or_create(*args, **kwargs):
            if kwargs.get('assinatura') == ass_erro:
                raise IntegrityError('conta invalida (simulado)')
            return original_get_or_create(*args, **kwargs)

        with mock.patch('financeiro.models.Receita.objects.get_or_create', side_effect=fake_get_or_create):
            resumo = gerar_cobrancas_mes(date(2026, 11, 1))

        self.assertEqual(resumo['criadas'], 2)
        self.assertEqual(len(resumo['erros']), 1)
        self.assertEqual(resumo['erros'][0]['assinatura_id'], ass_erro.pk)
        self.assertTrue(Receita.objects.filter(assinatura=ass_ok1).exists())
        self.assertTrue(Receita.objects.filter(assinatura=ass_ok2).exists())
        self.assertFalse(Receita.objects.filter(assinatura=ass_erro).exists())

    def test_assinatura_soft_deletada_nao_gera(self):
        assinatura = _make_assinatura(data_inicio=date(2026, 1, 1))
        assinatura.is_active = False
        assinatura.save()
        resumo = gerar_cobrancas_mes(date(2026, 11, 1))
        self.assertEqual(resumo['criadas'], 0)


class ReceitaUniqueConstraintTest(TestCase):
    """RF-07 — segunda camada de defesa contra race condition: constraint
    de banco, independente do get_or_create do service."""

    def test_constraint_db_bloqueia_duplicidade(self):
        assinatura = _make_assinatura(data_inicio=date(2026, 1, 1))
        kwargs = dict(
            assinatura=assinatura, referencia_mes=date(2026, 11, 1),
            tipo=TipoReceita.MENSALIDADE, descricao='teste',
            cliente=assinatura.cliente, categoria=assinatura.plano.categoria,
            valor_bruto=assinatura.valor, conta=assinatura.conta,
            vencimento=date(2026, 11, 10), status=StatusReceita.PENDENTE,
        )
        Receita.objects.create(**kwargs)
        with self.assertRaises(IntegrityError):
            Receita.objects.create(**kwargs)


class GerarCobrancasAssinaturasCommandTest(TestCase):
    def test_command_cria_receita_mes_corrente_por_default(self):
        _make_assinatura(data_inicio=date(2020, 1, 1))  # elegivel em qualquer mes (MENSAL, sem data_fim)
        call_command('gerar_cobrancas_assinaturas')
        self.assertEqual(Receita.objects.count(), 1)

    def test_command_dry_run_nao_persiste(self):
        _make_assinatura(data_inicio=date(2020, 1, 1))
        call_command('gerar_cobrancas_assinaturas', '--mes=2026-11', '--dry-run')
        self.assertEqual(Receita.objects.count(), 0)

    def test_command_mes_invalido_levanta_erro(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command('gerar_cobrancas_assinaturas', '--mes=2026-13')


class AssinaturaAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.cliente = _make_cliente()
        self.conta = _make_conta()
        self.plano = _make_plano(valor=Decimal('80.00'))

    def _payload(self, **extra):
        payload = {
            'cliente': self.cliente.id,
            'plano': self.plano.id,
            'dia_vencimento': 15,
            'data_inicio': '2026-01-01',
            'conta': self.conta.id,
        }
        payload.update(extra)
        return payload

    def test_criar_assinatura_copia_valor_do_plano_quando_omitido(self):
        resp = self.client.post('/api/v1/assinaturas/assinaturas/', self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(Decimal(resp.data['valor']), Decimal('80.00'))

    def test_criar_assinatura_valor_explicito_sobrescreve_plano(self):
        resp = self.client.post('/api/v1/assinaturas/assinaturas/', self._payload(valor='60.00'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(Decimal(resp.data['valor']), Decimal('60.00'))

    def test_rn02_dia_vencimento_fora_do_range_400(self):
        resp = self.client.post('/api/v1/assinaturas/assinaturas/', self._payload(dia_vencimento=30), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_data_fim_anterior_data_inicio_400(self):
        resp = self.client.post(
            '/api/v1/assinaturas/assinaturas/',
            self._payload(data_fim='2025-01-01'), format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rn10_payload_tentando_setar_status_encerrada_e_ignorado(self):
        resp = self.client.post(
            '/api/v1/assinaturas/assinaturas/',
            self._payload(status='ENCERRADA'), format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data['status'], StatusAssinatura.ATIVA)

    def test_id_e_primeiro_campo_da_serializacao(self):
        resp = self.client.post('/api/v1/assinaturas/assinaturas/', self._payload(), format='json')
        self.assertEqual(list(resp.data.keys())[0], 'id')

    def test_encerrar_assinatura(self):
        assinatura = _make_assinatura(cliente=self.cliente, plano=self.plano, conta=self.conta)
        resp = self.client.post(
            f'/api/v1/assinaturas/assinaturas/{assinatura.pk}/encerrar/',
            {'data_fim': '2026-06-30', 'motivo': 'cliente cancelou'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, StatusAssinatura.ENCERRADA)
        self.assertEqual(assinatura.data_fim, date(2026, 6, 30))
        self.assertEqual(assinatura.motivo_encerramento, 'cliente cancelou')
        self.assertIsNotNone(assinatura.encerrada_em)

    def test_rn07_encerrar_assinatura_ja_encerrada_400(self):
        assinatura = _make_assinatura(cliente=self.cliente, plano=self.plano, conta=self.conta)
        url = f'/api/v1/assinaturas/assinaturas/{assinatura.pk}/encerrar/'
        self.client.post(url, {'data_fim': '2026-06-30'}, format='json')
        resp2 = self.client.post(url, {'data_fim': '2026-07-30'}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_encerrar_sem_data_fim_400(self):
        assinatura = _make_assinatura(cliente=self.cliente, plano=self.plano, conta=self.conta)
        resp = self.client.post(
            f'/api/v1/assinaturas/assinaturas/{assinatura.pk}/encerrar/', {}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_encerrar_data_fim_anterior_data_inicio_400(self):
        assinatura = _make_assinatura(
            cliente=self.cliente, plano=self.plano, conta=self.conta, data_inicio=date(2026, 5, 1),
        )
        resp = self.client.post(
            f'/api/v1/assinaturas/assinaturas/{assinatura.pk}/encerrar/',
            {'data_fim': '2026-01-01'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pausar_e_retomar(self):
        assinatura = _make_assinatura(cliente=self.cliente, plano=self.plano, conta=self.conta)
        url_pausar = f'/api/v1/assinaturas/assinaturas/{assinatura.pk}/pausar/'
        resp = self.client.post(url_pausar)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, StatusAssinatura.PAUSADA)

        url_retomar = f'/api/v1/assinaturas/assinaturas/{assinatura.pk}/retomar/'
        resp = self.client.post(url_retomar)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, StatusAssinatura.ATIVA)

    def test_rn07_pausar_assinatura_encerrada_400(self):
        assinatura = _make_assinatura(cliente=self.cliente, plano=self.plano, conta=self.conta)
        self.client.post(
            f'/api/v1/assinaturas/assinaturas/{assinatura.pk}/encerrar/',
            {'data_fim': '2026-06-30'}, format='json',
        )
        resp = self.client.post(f'/api/v1/assinaturas/assinaturas/{assinatura.pk}/pausar/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rn07_retomar_assinatura_que_nao_esta_pausada_400(self):
        assinatura = _make_assinatura(cliente=self.cliente, plano=self.plano, conta=self.conta)
        resp = self.client.post(f'/api/v1/assinaturas/assinaturas/{assinatura.pk}/retomar/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rn07_retomar_assinatura_encerrada_400(self):
        assinatura = _make_assinatura(cliente=self.cliente, plano=self.plano, conta=self.conta)
        self.client.post(
            f'/api/v1/assinaturas/assinaturas/{assinatura.pk}/encerrar/',
            {'data_fim': '2026-06-30'}, format='json',
        )
        resp = self.client.post(f'/api/v1/assinaturas/assinaturas/{assinatura.pk}/retomar/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rnf02_delete_e_soft_delete(self):
        assinatura = _make_assinatura(cliente=self.cliente, plano=self.plano, conta=self.conta)
        resp = self.client.delete(f'/api/v1/assinaturas/assinaturas/{assinatura.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        assinatura.refresh_from_db()
        self.assertFalse(assinatura.is_active)
        self.assertIsNotNone(assinatura.deleted_at)
        self.assertEqual(assinatura.deleted_by_id, self.user.id)

    def test_rnf03_created_by_preenchido_automaticamente(self):
        resp = self.client.post('/api/v1/assinaturas/assinaturas/', self._payload(), format='json')
        assinatura = Assinatura.objects.get(pk=resp.data['id'])
        self.assertEqual(assinatura.created_by_id, self.user.id)

    def test_ca09_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/assinaturas/assinaturas/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ca09_perfil_sem_acesso_403(self):
        user_comum = _make_user(email='comum@teste.com', is_staff=False, perfil='OPERACIONAL')
        self.client.force_authenticate(user_comum)
        resp = self.client.get('/api/v1/assinaturas/assinaturas/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_perfil_financeiro_tem_acesso(self):
        user_financeiro = _make_user(email='fin@teste.com', is_staff=False, perfil='FINANCEIRO')
        self.client.force_authenticate(user_financeiro)
        resp = self.client.get('/api/v1/assinaturas/assinaturas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class PlanoAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.categoria = _make_categoria()

    def test_criar_e_listar_plano(self):
        resp = self.client.post('/api/v1/assinaturas/planos/', {
            'nome': 'Plano Mensal',
            'valor': '99.90',
            'periodicidade': 'MENSAL',
            'categoria': self.categoria.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        resp_list = self.client.get('/api/v1/assinaturas/planos/')
        self.assertEqual(resp_list.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_list.data['count'], 1)

    def test_rnf02_delete_plano_e_soft_delete(self):
        resp = self.client.post('/api/v1/assinaturas/planos/', {
            'nome': 'Plano X', 'valor': '10.00', 'periodicidade': 'MENSAL', 'categoria': self.categoria.id,
        }, format='json')
        plano_id = resp.data['id']
        del_resp = self.client.delete(f'/api/v1/assinaturas/planos/{plano_id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)
        plano = Plano.all_objects.get(pk=plano_id)
        self.assertFalse(plano.is_active)
        self.assertIsNotNone(plano.deleted_at)


class ReceitaFiltroAssinaturaTest(APITestCase):
    """RF-11 (ponta backend) — filtro de Receita por assinatura/cliente
    usado pela aba Assinaturas na ficha do Cliente."""

    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)

    def test_filtro_por_assinatura(self):
        assinatura = _make_assinatura(data_inicio=date(2026, 1, 1))
        gerar_cobrancas_mes(date(2026, 11, 1))
        receita = Receita.objects.get(assinatura=assinatura)

        resp = self.client.get(f'/api/v1/financeiro/receitas/?assinatura={assinatura.pk}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in resp.data['results']]
        self.assertIn(receita.id, ids)

    def test_filtro_por_cliente_inclui_receitas_de_assinatura(self):
        assinatura = _make_assinatura(data_inicio=date(2026, 1, 1))
        gerar_cobrancas_mes(date(2026, 11, 1))

        resp = self.client.get(f'/api/v1/financeiro/receitas/?cliente={assinatura.cliente_id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['assinatura'], assinatura.pk)
