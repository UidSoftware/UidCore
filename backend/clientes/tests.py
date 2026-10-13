"""Testes do app clientes — Fase A da Manutenção #11.

Cobre: campos cpf/cnpj, AcionistaCliente, endpoints de acionistas.
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import AcionistaCliente, Cliente, HistoricoCliente


def _make_user(email='admin@teste.com'):
    return User.objects.create_user(email=email, password='senha123', nome_completo='Admin Teste')


def _make_cliente_pj(nome='Empresa Teste'):
    return Cliente.objects.create(
        nome_razao_social=nome, tipo_pessoa='PJ', cnpj='12345678000190',
    )


def _make_cliente_pf(nome='Pessoa Teste'):
    return Cliente.objects.create(
        nome_razao_social=nome, tipo_pessoa='PF', cpf='12345678901',
    )


class ClienteCpfCnpjModelTest(TestCase):
    def test_cliente_pj_armazena_cnpj(self):
        cliente = _make_cliente_pj()
        cliente.refresh_from_db()
        self.assertEqual(cliente.cnpj, '12345678000190')
        self.assertEqual(cliente.cpf, '')

    def test_cliente_pf_armazena_cpf(self):
        cliente = _make_cliente_pf()
        cliente.refresh_from_db()
        self.assertEqual(cliente.cpf, '12345678901')
        self.assertEqual(cliente.cnpj, '')

    def test_campo_documento_ainda_existe(self):
        # Garantir que documento nao foi removido (compatibilidade)
        cliente = Cliente.objects.create(
            nome_razao_social='Compat', tipo_pessoa='PJ',
            documento='12345678000199',
        )
        self.assertIsNotNone(cliente.documento)


class AcionistaClienteModelTest(TestCase):
    def setUp(self):
        self.cliente = _make_cliente_pj()

    def test_criar_acionista_basico(self):
        ac = AcionistaCliente.objects.create(
            cliente=self.cliente, nome='João Silva', email='joao@teste.com',
            cpf='11122233344',
        )
        self.assertEqual(ac.nome, 'João Silva')
        self.assertEqual(ac.cliente, self.cliente)
        self.assertFalse(ac.principal)

    def test_principal_true_desmarca_outros(self):
        ac1 = AcionistaCliente.objects.create(
            cliente=self.cliente, nome='Sócio 1', principal=True,
        )
        ac2 = AcionistaCliente.objects.create(
            cliente=self.cliente, nome='Sócio 2', principal=True,
        )
        ac1.refresh_from_db()
        # ac2 é principal; ac1 deve ter sido desmarcado
        self.assertFalse(ac1.principal)
        self.assertTrue(ac2.principal)

    def test_soft_delete_via_is_active(self):
        ac = AcionistaCliente.objects.create(cliente=self.cliente, nome='Para Remover')
        ac.is_active = False
        ac.save()
        self.assertFalse(AcionistaCliente.objects.get(pk=ac.pk).is_active)


class AcionistaClienteAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.cliente = _make_cliente_pj()

    def test_listar_acionistas_get(self):
        AcionistaCliente.objects.create(cliente=self.cliente, nome='Sócio A')
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/acionistas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_criar_acionista_post(self):
        resp = self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/acionistas/',
            {'nome': 'Novo Sócio', 'email': 'socio@teste.com', 'principal': True},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', resp.data)

    def test_patch_acionista(self):
        ac = AcionistaCliente.objects.create(cliente=self.cliente, nome='Old Name')
        resp = self.client.patch(
            f'/api/v1/clientes/{self.cliente.id}/acionistas/{ac.id}/',
            {'nome': 'New Name'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['nome'], 'New Name')

    def test_delete_acionista_soft_delete(self):
        ac = AcionistaCliente.objects.create(cliente=self.cliente, nome='Para Deletar')
        resp = self.client.delete(f'/api/v1/clientes/{self.cliente.id}/acionistas/{ac.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        ac.refresh_from_db()
        self.assertFalse(ac.is_active)

    def test_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/acionistas/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cpf_cnpj_no_serializer_cliente(self):
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('cpf', resp.data)
        self.assertIn('cnpj', resp.data)
        self.assertIn('acionistas', resp.data)


class AuditoriaManutencao62APITest(APITestCase):
    """Manutencao 62 — ciclo completo created_by/updated_by/deleted_by/deleted_at."""

    def test_ciclo_completo_auditoria_cliente(self):
        user_a = _make_user(email='a62@teste.com')
        user_b = _make_user(email='b62@teste.com')
        user_c = _make_user(email='c62@teste.com')

        self.client.force_authenticate(user_a)
        resp = self.client.post('/api/v1/clientes/', {'nome_razao_social': 'Cliente Auditoria'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        cliente_id = resp.data['id']
        cliente = Cliente.objects.get(pk=cliente_id)
        self.assertEqual(cliente.created_by, user_a)

        self.client.force_authenticate(user_b)
        resp = self.client.patch(f'/api/v1/clientes/{cliente_id}/', {'telefone': '11999998888'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        cliente.refresh_from_db()
        self.assertEqual(cliente.updated_by, user_b)
        self.assertEqual(cliente.created_by, user_a)

        self.client.force_authenticate(user_c)
        resp = self.client.delete(f'/api/v1/clientes/{cliente_id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        cliente = Cliente.all_objects.get(pk=cliente_id)
        self.assertEqual(cliente.deleted_by, user_c)
        self.assertIsNotNone(cliente.deleted_at)
        self.assertFalse(Cliente.objects.filter(pk=cliente_id).exists())


# --- Manutencao 63 [NUCLEO 2/5] (RF-06) — BloqueiaEscritaDeProfissional ---
# Cobre CA-06, CA-07 e CA-11 (parte clientes) da Especificacao_Hotfix.md.

def _make_profissional(email='profissional-cli@teste.com'):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Profissional Teste',
        perfil='PROFISSIONAL', is_staff=False,
    )


def _make_operacional_cliente(email='operacional-cli@teste.com'):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Operacional Teste', is_staff=False,
    )


def _make_marketing_cliente(email='marketing-cli@teste.com'):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Marketing Teste',
        perfil='MARKETING', is_staff=False,
    )


def _make_financeiro_cliente(email='financeiro-cli@teste.com'):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Financeiro Teste',
        perfil='FINANCEIRO', is_staff=False,
    )


class BloqueiaEscritaDeProfissionalAPITest(APITestCase):
    def setUp(self):
        self.cliente = _make_cliente_pj('Cliente Bloqueio')

    def test_profissional_le_lista_completa_ca06(self):
        self.client.force_authenticate(_make_profissional())
        resp = self.client.get('/api/v1/clientes/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data['results']), 1)

    def test_profissional_post_bloqueado_ca07(self):
        self.client.force_authenticate(_make_profissional())
        resp = self.client.post('/api/v1/clientes/', {'nome_razao_social': 'Novo Cliente'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_profissional_patch_bloqueado(self):
        self.client.force_authenticate(_make_profissional())
        resp = self.client.patch(f'/api/v1/clientes/{self.cliente.id}/', {'telefone': '11988887777'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_profissional_delete_bloqueado(self):
        self.client.force_authenticate(_make_profissional())
        resp = self.client.delete(f'/api/v1/clientes/{self.cliente.id}/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_profissional_post_historico_bloqueado(self):
        self.client.force_authenticate(_make_profissional())
        resp = self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/historico/',
            {'descricao': 'Contato realizado'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_profissional_post_acionistas_bloqueado(self):
        self.client.force_authenticate(_make_profissional())
        resp = self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/acionistas/',
            {'nome': 'Socio Teste', 'percentual': '50.00'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_operacional_post_sem_regressao_ca11(self):
        self.client.force_authenticate(_make_operacional_cliente())
        resp = self.client.post('/api/v1/clientes/', {'nome_razao_social': 'Cliente Operacional'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_marketing_post_sem_regressao_ca11(self):
        self.client.force_authenticate(_make_marketing_cliente())
        resp = self.client.post('/api/v1/clientes/', {'nome_razao_social': 'Cliente Marketing'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_financeiro_post_sem_regressao(self):
        self.client.force_authenticate(_make_financeiro_cliente())
        resp = self.client.post('/api/v1/clientes/', {'nome_razao_social': 'Cliente Financeiro'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_admin_tem_acesso_total_post_permitido_ca10(self):
        admin = User.objects.create_user(
            email='admin-cli-m63@teste.com', password='senha123',
            nome_completo='Admin Teste', is_staff=True,
        )
        self.client.force_authenticate(admin)
        resp = self.client.post('/api/v1/clientes/', {'nome_razao_social': 'Cliente Admin'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


# --- Manutencao #66 [NUCLEO 5/5] — LGPD: exportacao e anonimizacao do
# titular. Cobre CA-01 a CA-10 da Especificacao_Hotfix.md (CA-11, build do
# container, verificado manualmente pelo Forge — nao testavel via Django
# TestCase). ---

from common.models import ExportacaoTitular  # noqa: E402


def _make_admin_lgpd(email='admin-lgpd@teste.com'):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Admin LGPD', is_staff=True,
    )


def _make_cliente_com_dado_pessoal(nome='Titular LGPD'):
    return Cliente.objects.create(
        nome_razao_social=nome, tipo_pessoa='PF', cpf='98765432100',
        telefone='34999998888', email='titular@teste.com',
        endereco='Rua Teste, 123', cidade='Uberlândia', estado='MG', cep='38400000',
        observacoes='Observação pessoal do titular',
    )


class ClienteExportarAPITest(APITestCase):
    def setUp(self):
        self.cliente = _make_cliente_com_dado_pessoal()

    def test_exportar_json_200_e_contem_secao_clientes_ca02(self):
        self.client.force_authenticate(_make_admin_lgpd())
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/exportar/?formato=json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('cliente', resp.data)
        self.assertIn('secoes', resp.data)
        apps = [s['app'] for s in resp.data['secoes']]
        self.assertIn('clientes', apps)
        secao_clientes = next(s for s in resp.data['secoes'] if s['app'] == 'clientes')
        self.assertEqual(
            secao_clientes['dados']['cadastro']['nome_razao_social'], 'Titular LGPD'
        )

    def test_exportar_default_sem_formato_e_json(self):
        self.client.force_authenticate(_make_admin_lgpd())
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/exportar/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('secoes', resp.data)

    def test_exportar_pdf_200_content_type_pdf_ca01(self):
        self.client.force_authenticate(_make_admin_lgpd())
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/exportar/?formato=pdf')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))

    def test_exportar_formato_invalido_400(self):
        self.client.force_authenticate(_make_admin_lgpd())
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/exportar/?formato=xml')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_exportar_cria_exportacao_titular_ca03(self):
        admin = _make_admin_lgpd()
        self.client.force_authenticate(admin)
        self.assertEqual(ExportacaoTitular.objects.filter(cliente=self.cliente).count(), 0)
        self.client.get(f'/api/v1/clientes/{self.cliente.id}/exportar/?formato=json')
        self.assertEqual(ExportacaoTitular.objects.filter(cliente=self.cliente).count(), 1)
        exportacao = ExportacaoTitular.objects.get(cliente=self.cliente)
        self.assertEqual(exportacao.formato, 'JSON')
        self.assertEqual(exportacao.created_by, admin)

    def test_exportar_pdf_tambem_cria_exportacao_titular_formato_pdf(self):
        self.client.force_authenticate(_make_admin_lgpd())
        self.client.get(f'/api/v1/clientes/{self.cliente.id}/exportar/?formato=pdf')
        exportacao = ExportacaoTitular.objects.get(cliente=self.cliente)
        self.assertEqual(exportacao.formato, 'PDF')

    def test_exportar_sem_permissao_403_ca10(self):
        self.client.force_authenticate(_make_operacional_cliente())
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/exportar/?formato=json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_exportar_profissional_403_ca10(self):
        self.client.force_authenticate(_make_profissional())
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/exportar/?formato=json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_exportar_sem_autenticacao_403(self):
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/exportar/?formato=json')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_exportar_agrega_secao_de_outro_app_financeiro_ca01(self):
        from financeiro.models import Conta, Receita

        conta = Conta.objects.create(nome='Conta Teste LGPD')
        Receita.objects.create(
            cliente=self.cliente, conta=conta, descricao='Mensalidade Teste',
            valor_bruto=Decimal('150.00'),
        )
        self.client.force_authenticate(_make_admin_lgpd())
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/exportar/?formato=json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        apps = [s['app'] for s in resp.data['secoes']]
        self.assertIn('financeiro', apps)
        secao_financeiro = next(s for s in resp.data['secoes'] if s['app'] == 'financeiro')
        self.assertEqual(secao_financeiro['dados']['receitas'][0]['descricao'], 'Mensalidade Teste')

    def test_exportar_nao_vaza_pk_de_usuario_rnf04(self):
        # RNF-04: a secao de portal expoe email, nunca o id interno do User.
        from portal.models import AcessoPortalCliente

        usuario = User.objects.create_user(
            email='titular-portal@teste.com', password='senha123', nome_completo='Titular Portal',
        )
        AcessoPortalCliente.objects.create(cliente=self.cliente, usuario=usuario)
        self.client.force_authenticate(_make_admin_lgpd())
        resp = self.client.get(f'/api/v1/clientes/{self.cliente.id}/exportar/?formato=json')
        secao_portal = next(s for s in resp.data['secoes'] if s['app'] == 'portal')
        acesso = secao_portal['dados']['acessos'][0]
        self.assertEqual(acesso['usuario_email'], 'titular-portal@teste.com')
        self.assertNotIn('usuario_id', acesso)
        self.assertNotIn('id', acesso)


class ClienteAnonimizarAPITest(APITestCase):
    def setUp(self):
        self.cliente = _make_cliente_com_dado_pessoal()
        self.admin = _make_admin_lgpd()

    def _exportar(self, cliente=None):
        cliente = cliente or self.cliente
        self.client.force_authenticate(self.admin)
        return self.client.get(f'/api/v1/clientes/{cliente.id}/exportar/?formato=json')

    def test_anonimizar_sem_exportacao_previa_400_ca04(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/anonimizar/', {'confirmo': True}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.anonimizado)

    def test_anonimizar_sem_confirmo_400_ca06(self):
        self._exportar()
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f'/api/v1/clientes/{self.cliente.id}/anonimizar/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonimizar_confirmo_false_400_ca06(self):
        self._exportar()
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/anonimizar/', {'confirmo': False}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonimizar_com_exportacao_e_confirmo_200_ca05(self):
        self._exportar()
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/anonimizar/', {'confirmo': True}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.anonimizado)
        self.assertEqual(self.cliente.nome_razao_social, f'Titular anonimizado #{self.cliente.id}')
        self.assertIsNone(self.cliente.documento)
        self.assertEqual(self.cliente.cpf, '')
        self.assertEqual(self.cliente.telefone, '')
        self.assertEqual(self.cliente.email, '')
        self.assertEqual(self.cliente.endereco, '')
        self.assertEqual(self.cliente.observacoes, '')
        self.assertIsNotNone(self.cliente.anonimizado_em)
        self.assertEqual(self.cliente.anonimizado_por, self.admin)

    def test_anonimizar_some_das_buscas_por_nome_antigo_ca05(self):
        self._exportar()
        self.client.force_authenticate(self.admin)
        self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/anonimizar/', {'confirmo': True}, format='json',
        )
        resp = self.client.get('/api/v1/clientes/?search=Titular LGPD')
        resultados = resp.data['results'] if 'results' in resp.data else resp.data
        ids = [r['id'] for r in resultados]
        self.assertNotIn(self.cliente.id, ids)

    def test_anonimizar_duas_vezes_400_ca07(self):
        self._exportar()
        self.client.force_authenticate(self.admin)
        self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/anonimizar/', {'confirmo': True}, format='json',
        )
        resp = self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/anonimizar/', {'confirmo': True}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonimizar_sem_permissao_403_ca10(self):
        self._exportar()
        self.client.force_authenticate(_make_operacional_cliente())
        resp = self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/anonimizar/', {'confirmo': True}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonimizar_mantem_receita_intacta_ca08(self):
        from financeiro.models import Conta, Receita

        conta = Conta.objects.create(nome='Conta Teste LGPD 2')
        receita = Receita.objects.create(
            cliente=self.cliente, conta=conta, descricao='Mensalidade Intacta',
            valor_bruto=Decimal('200.00'),
        )
        self._exportar()
        self.client.force_authenticate(self.admin)
        self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/anonimizar/', {'confirmo': True}, format='json',
        )
        receita.refresh_from_db()
        self.assertEqual(str(receita.valor_bruto), '200.00')
        self.assertEqual(receita.descricao, 'Mensalidade Intacta')
        self.assertEqual(receita.cliente_id, self.cliente.id)

    def test_anonimizar_remove_descricao_historico(self):
        HistoricoCliente.objects.create(cliente=self.cliente, descricao='Dado pessoal sensível')
        self._exportar()
        self.client.force_authenticate(self.admin)
        self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/anonimizar/', {'confirmo': True}, format='json',
        )
        historico = HistoricoCliente.objects.get(cliente=self.cliente)
        self.assertEqual(historico.descricao, '[conteúdo removido por anonimização LGPD]')

    def test_anonimizar_acionista(self):
        acionista = AcionistaCliente.objects.create(
            cliente=self.cliente, nome='Sócio Pessoal', email='socio@teste.com',
            cpf='11122233344', telefone='34988887777',
        )
        self._exportar()
        self.client.force_authenticate(self.admin)
        self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/anonimizar/', {'confirmo': True}, format='json',
        )
        acionista.refresh_from_db()
        self.assertEqual(acionista.nome, f'Acionista anonimizado #{acionista.pk}')
        self.assertEqual(acionista.email, '')
        self.assertEqual(acionista.cpf, '')
        self.assertEqual(acionista.telefone, '')

    def test_segundo_cliente_anonimizado_documento_nao_conflita(self):
        cliente2 = _make_cliente_com_dado_pessoal('Segundo Titular')
        self._exportar()
        self._exportar(cliente2)

        self.client.force_authenticate(self.admin)
        resp1 = self.client.post(
            f'/api/v1/clientes/{self.cliente.id}/anonimizar/', {'confirmo': True}, format='json',
        )
        resp2 = self.client.post(
            f'/api/v1/clientes/{cliente2.id}/anonimizar/', {'confirmo': True}, format='json',
        )
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        cliente2.refresh_from_db()
        self.assertIsNone(cliente2.documento)
