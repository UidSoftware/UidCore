"""Testes do app marketing (Manutencao #54).

Cobre RF01-RF05 e RN01-RN08 da Especificacao_Hotfix.md:
- CRUD de Campanha e Lead (RF01/RF02) + soft delete (RN02)
- Acao converter (RF03) com/sem duplicidade de e-mail + irreversibilidade (RN06)
- Endpoint ROI/CAC por campanha (RF04) com casos de divisor zero
- Perfil MARKETING (RF05) + permissao IsMarketing (RN08)
- Exposicao do campo perfil via /accounts/me/ e /accounts/usuarios/{id}/
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from clientes.models import Cliente
from vendas.models import Pedido

from .models import Campanha, Lead, StatusLead


def _make_admin(email='admin@teste.com'):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Admin Teste', is_staff=True,
    )


def _make_marketing(email='marketing@teste.com'):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Marketing Teste', perfil='MARKETING',
    )


def _make_operacional(email='operacional@teste.com'):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Operacional Teste',
    )


def _make_campanha(nome='Campanha Teste', orcamento=Decimal('1000.00'), data_inicio=None):
    return Campanha.objects.create(
        nome=nome, canal='ads', data_inicio=data_inicio or date(2026, 1, 1), orcamento=orcamento,
    )


def _make_lead(nome='Lead Teste', email='lead@teste.com', campanha=None):
    return Lead.objects.create(nome=nome, email=email, campanha=campanha)


# --- RF01/RN02 — Campanha model + soft delete -----------------------------

class CampanhaModelTest(TestCase):
    def test_criar_campanha_valida(self):
        campanha = _make_campanha()
        self.assertEqual(campanha.status, 'planejada')
        self.assertTrue(campanha.is_active)

    def test_soft_delete_campanha_nao_remove_do_banco(self):
        campanha = _make_campanha()
        campanha.is_active = False
        campanha.save(update_fields=['is_active', 'updated_at'])
        self.assertTrue(Campanha.objects.filter(pk=campanha.pk).exists())
        self.assertFalse(Campanha.objects.get(pk=campanha.pk).is_active)


# --- RF02/RN07 — Lead model ------------------------------------------------

class LeadModelTest(TestCase):
    def test_criar_lead_sem_campanha(self):
        lead = _make_lead(campanha=None)
        self.assertIsNone(lead.campanha)
        self.assertEqual(lead.status, StatusLead.NOVO)

    def test_lead_mantem_historico_apos_campanha_arquivada_rn07(self):
        campanha = _make_campanha()
        lead = _make_lead(campanha=campanha)
        campanha.is_active = False
        campanha.save(update_fields=['is_active', 'updated_at'])
        lead.refresh_from_db()
        self.assertEqual(lead.campanha_id, campanha.pk)


# --- CRUD via API (CA-01 a CA-05) -----------------------------------------

class CampanhaAPITest(APITestCase):
    def setUp(self):
        self.admin = _make_admin()
        self.client.force_authenticate(self.admin)

    def test_criar_campanha_ca01(self):
        resp = self.client.post('/api/v1/marketing/campanhas/', {
            'nome': 'Campanha Ads Julho', 'canal': 'ads',
            'data_inicio': '2026-07-01', 'orcamento': '500.00',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_listar_campanhas_apenas_ativas_ca02(self):
        ativa = _make_campanha(nome='Ativa')
        inativa = _make_campanha(nome='Inativa')
        inativa.is_active = False
        inativa.save(update_fields=['is_active', 'updated_at'])
        resp = self.client.get('/api/v1/marketing/campanhas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        nomes = [c['nome'] for c in resp.data['results']]
        self.assertIn('Ativa', nomes)
        self.assertNotIn('Inativa', nomes)

    def test_excluir_campanha_soft_delete_ca03(self):
        campanha = _make_campanha()
        resp = self.client.delete(f'/api/v1/marketing/campanhas/{campanha.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        campanha.refresh_from_db()
        self.assertFalse(campanha.is_active)
        self.assertTrue(Campanha.objects.filter(pk=campanha.pk).exists())


class LeadAPITest(APITestCase):
    def setUp(self):
        self.admin = _make_admin()
        self.client.force_authenticate(self.admin)
        self.campanha = _make_campanha()

    def test_criar_lead_com_campanha_ca04(self):
        resp = self.client.post('/api/v1/marketing/leads/', {
            'nome': 'Lead Novo', 'email': 'novo@teste.com', 'campanha': self.campanha.pk,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['campanha'], self.campanha.pk)

    def test_criar_lead_sem_campanha_ca05(self):
        resp = self.client.post('/api/v1/marketing/leads/', {
            'nome': 'Lead Organico', 'email': 'organico@teste.com',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(resp.data['campanha'])


# --- RF03/RN06 — conversao em cliente (CA-06 a CA-08) ----------------------

class ConverterLeadTest(APITestCase):
    def setUp(self):
        self.admin = _make_admin()
        self.client.force_authenticate(self.admin)
        self.campanha = _make_campanha(nome='Campanha Origem')

    def test_converter_com_email_existente_vincula_cliente_ca06(self):
        cliente = Cliente.objects.create(
            tipo_pessoa='PF', nome_razao_social='Ja Cliente', email='ja@teste.com',
        )
        lead = _make_lead(nome='Lead Duplicado', email='ja@teste.com', campanha=self.campanha)

        total_clientes_antes = Cliente.objects.count()
        resp = self.client.post(f'/api/v1/marketing/leads/{lead.pk}/converter/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Cliente.objects.count(), total_clientes_antes)
        lead.refresh_from_db()
        self.assertEqual(lead.cliente_convertido_id, cliente.pk)
        self.assertEqual(lead.status, StatusLead.CONVERTIDO)

    def test_converter_com_email_novo_cria_cliente_com_origem_ca07(self):
        lead = _make_lead(nome='Lead Novo', email='novissimo@teste.com', campanha=self.campanha)
        resp = self.client.post(f'/api/v1/marketing/leads/{lead.pk}/converter/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        lead.refresh_from_db()
        self.assertIsNotNone(lead.cliente_convertido)
        self.assertEqual(lead.cliente_convertido.origem, 'Campanha Origem')

    def test_converter_lead_sem_campanha_usa_origem_padrao(self):
        lead = _make_lead(nome='Lead Sem Campanha', email='semcamp@teste.com', campanha=None)
        resp = self.client.post(f'/api/v1/marketing/leads/{lead.pk}/converter/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        lead.refresh_from_db()
        self.assertEqual(lead.cliente_convertido.origem, 'Sem campanha')

    def test_converter_duas_vezes_retorna_400_ca08(self):
        lead = _make_lead(nome='Lead Unico', email='unico@teste.com', campanha=self.campanha)
        primeira = self.client.post(f'/api/v1/marketing/leads/{lead.pk}/converter/')
        segunda = self.client.post(f'/api/v1/marketing/leads/{lead.pk}/converter/')

        self.assertEqual(primeira.status_code, status.HTTP_200_OK)
        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_nao_reverte_status_convertido_rn06(self):
        lead = _make_lead(nome='Lead Convertido', email='convertido@teste.com', campanha=self.campanha)
        self.client.post(f'/api/v1/marketing/leads/{lead.pk}/converter/')

        resp = self.client.patch(f'/api/v1/marketing/leads/{lead.pk}/', {'status': 'novo'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# --- RF04 — ROI/CAC (CA-09 a CA-11) ----------------------------------------

class RoiCampanhaTest(APITestCase):
    def setUp(self):
        self.admin = _make_admin()
        self.client.force_authenticate(self.admin)

    def test_roi_sem_leads_convertidos_cac_null_ca09(self):
        campanha = _make_campanha(orcamento=Decimal('300.00'))
        _make_lead(nome='Lead1', email='l1@teste.com', campanha=campanha)

        resp = self.client.get(f'/api/v1/marketing/campanhas/{campanha.pk}/roi/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data['cac'])
        self.assertEqual(resp.data['leads_total'], 1)
        self.assertEqual(resp.data['leads_convertidos'], 0)

    def test_roi_orcamento_zero_roi_null_ca10(self):
        campanha = _make_campanha(orcamento=Decimal('0'))
        lead = _make_lead(nome='Lead1', email='l1@teste.com', campanha=campanha)
        self.client.post(f'/api/v1/marketing/leads/{lead.pk}/converter/')

        resp = self.client.get(f'/api/v1/marketing/campanhas/{campanha.pk}/roi/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data['roi'])
        self.assertIsNotNone(resp.data['cac'])
        self.assertEqual(Decimal(str(resp.data['cac'])), Decimal('0'))

    def test_roi_soma_multiplos_pedidos_mesmo_cliente_ca11(self):
        campanha = _make_campanha(orcamento=Decimal('100.00'), data_inicio=date(2026, 1, 1))
        lead = _make_lead(nome='Lead Convertido', email='conv@teste.com', campanha=campanha)
        resp_conv = self.client.post(f'/api/v1/marketing/leads/{lead.pk}/converter/')
        cliente_id = resp_conv.data['cliente_convertido']

        Pedido.objects.create(cliente_id=cliente_id, valor_total=Decimal('200.00'))
        Pedido.objects.create(cliente_id=cliente_id, valor_total=Decimal('150.00'))

        resp = self.client.get(f'/api/v1/marketing/campanhas/{campanha.pk}/roi/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(resp.data['receita_fechada'])), Decimal('350.00'))
        self.assertEqual(Decimal(str(resp.data['cac'])), Decimal('100.00'))
        # roi = ((350 - 100) / 100) * 100 = 250
        self.assertEqual(Decimal(str(resp.data['roi'])), Decimal('250.00'))


# --- RF05/RN08 — permissoes por perfil (CA-12 a CA-14) ---------------------

class PermissaoMarketingTest(APITestCase):
    def test_operacional_sem_acesso_ca12(self):
        self.client.force_authenticate(_make_operacional())
        resp = self.client.get('/api/v1/marketing/campanhas/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_marketing_acessa_campanhas_e_leads_ca13(self):
        self.client.force_authenticate(_make_marketing())
        resp_campanhas = self.client.get('/api/v1/marketing/campanhas/')
        resp_leads = self.client.get('/api/v1/marketing/leads/')
        self.assertEqual(resp_campanhas.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_leads.status_code, status.HTTP_200_OK)

    def test_marketing_sem_acesso_financeiro_ca13(self):
        self.client.force_authenticate(_make_marketing())
        # aportes/ exige IsAdmin puro (RN08) — usuario MARKETING (is_staff=False) nunca pode ser 200
        resp = self.client.get('/api/v1/financeiro/aportes/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_acessa_marketing_mesmo_com_perfil_operacional_ca14(self):
        admin = _make_admin()
        admin.perfil = 'OPERACIONAL'
        admin.save(update_fields=['perfil'])
        self.client.force_authenticate(admin)
        resp = self.client.get('/api/v1/marketing/campanhas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# --- RF05 — exposicao do campo perfil (CA-15/CA-16) ------------------------

class PerfilExposicaoTest(APITestCase):
    def test_me_retorna_perfil_ca15(self):
        marketing = _make_marketing()
        self.client.force_authenticate(marketing)
        resp = self.client.get('/api/v1/accounts/me/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['perfil'], 'MARKETING')

    def test_admin_altera_perfil_de_usuario_ca16(self):
        admin = _make_admin()
        alvo = _make_operacional()
        self.client.force_authenticate(admin)
        resp = self.client.patch(f'/api/v1/accounts/usuarios/{alvo.pk}/', {'perfil': 'MARKETING'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        alvo.refresh_from_db()
        self.assertEqual(alvo.perfil, 'MARKETING')
