"""Testes de `common/permissions.py` — Manutencao 63 [NUCLEO 2/5] (RF-02/RF-09/CA-13).

Unitarios, sem HTTP real (request mockado via RequestFactory) — cobrem
IsFinanceiro, IsProfissional e BloqueiaEscritaDeProfissional isoladas,
nos dois sentidos (permite/bloqueia), conforme a tabela da secao 2.5 da
Especificacao_Hotfix.md. Os testes de integracao via API real (contas,
estornar, compras, agendamento, clientes) ficam nos apps respectivos.
"""
from django.test import RequestFactory, TestCase

from accounts.models import User
from common.permissions import BloqueiaEscritaDeProfissional, IsFinanceiro, IsProfissional


def _make_user(email, perfil='OPERACIONAL', is_staff=False):
    return User.objects.create_user(
        email=email, password='senha123', nome_completo='Usuario Teste',
        perfil=perfil, is_staff=is_staff,
    )


class IsFinanceiroTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_perfil_financeiro_tem_permissao(self):
        user = _make_user('financeiro@teste.com', perfil='FINANCEIRO')
        request = self.factory.get('/')
        request.user = user
        self.assertTrue(IsFinanceiro().has_permission(request, None))

    def test_perfil_operacional_sem_permissao(self):
        user = _make_user('operacional@teste.com', perfil='OPERACIONAL')
        request = self.factory.get('/')
        request.user = user
        self.assertFalse(IsFinanceiro().has_permission(request, None))

    def test_tem_acesso_total_passa_mesmo_sem_perfil_financeiro(self):
        admin = _make_user('admin-fin@teste.com', perfil='ADMIN')
        request = self.factory.get('/')
        request.user = admin
        self.assertTrue(IsFinanceiro().has_permission(request, None))


class IsProfissionalTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_perfil_profissional_tem_permissao(self):
        user = _make_user('prof@teste.com', perfil='PROFISSIONAL')
        request = self.factory.get('/')
        request.user = user
        self.assertTrue(IsProfissional().has_permission(request, None))

    def test_perfil_operacional_sem_permissao(self):
        user = _make_user('operacional2@teste.com', perfil='OPERACIONAL')
        request = self.factory.get('/')
        request.user = user
        self.assertFalse(IsProfissional().has_permission(request, None))

    def test_tem_acesso_total_passa_mesmo_sem_perfil_profissional(self):
        admin = _make_user('admin-prof@teste.com', perfil='ADMIN')
        request = self.factory.get('/')
        request.user = admin
        self.assertTrue(IsProfissional().has_permission(request, None))


class BloqueiaEscritaDeProfissionalTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_profissional_get_permitido(self):
        user = _make_user('prof-get@teste.com', perfil='PROFISSIONAL')
        request = self.factory.get('/')
        request.user = user
        self.assertTrue(BloqueiaEscritaDeProfissional().has_permission(request, None))

    def test_profissional_post_bloqueado(self):
        user = _make_user('prof-post@teste.com', perfil='PROFISSIONAL')
        request = self.factory.post('/')
        request.user = user
        self.assertFalse(BloqueiaEscritaDeProfissional().has_permission(request, None))

    def test_profissional_patch_bloqueado(self):
        user = _make_user('prof-patch@teste.com', perfil='PROFISSIONAL')
        request = self.factory.patch('/')
        request.user = user
        self.assertFalse(BloqueiaEscritaDeProfissional().has_permission(request, None))

    def test_profissional_delete_bloqueado(self):
        user = _make_user('prof-delete@teste.com', perfil='PROFISSIONAL')
        request = self.factory.delete('/')
        request.user = user
        self.assertFalse(BloqueiaEscritaDeProfissional().has_permission(request, None))

    def test_admin_tem_acesso_total_post_permitido(self):
        admin = _make_user('admin-bloqueio@teste.com', perfil='ADMIN')
        request = self.factory.post('/')
        request.user = admin
        self.assertTrue(BloqueiaEscritaDeProfissional().has_permission(request, None))

    def test_operacional_post_permitido_sem_regressao(self):
        user = _make_user('operacional-post@teste.com', perfil='OPERACIONAL')
        request = self.factory.post('/')
        request.user = user
        self.assertTrue(BloqueiaEscritaDeProfissional().has_permission(request, None))

    def test_nao_autenticado_bloqueado(self):
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get('/')
        request.user = AnonymousUser()
        self.assertFalse(BloqueiaEscritaDeProfissional().has_permission(request, None))


# --- Manutencao #66 [NUCLEO 5/5] — RF-01/RF-07/RN-04/CA-09: registry de
# exportacao LGPD. Cobre que o nucleo (common/lgpd.py) nao precisa
# conhecer o app_label com antecedencia — um app "fake" criado dentro do
# proprio teste se registra e aparece em exportar_tudo(), sem alterar
# common/. ---

class LgpdRegistryTest(TestCase):
    def setUp(self):
        from common import lgpd
        self._lgpd = lgpd
        # Isola o registry global entre testes — nao queremos que um
        # app_label fake registrado aqui vaze pros demais testes do
        # processo (e vice-versa, nao queremos perder os registros reais
        # dos apps de negocio feitos em AppConfig.ready()).
        self._registry_original = dict(lgpd._REGISTRY)

    def tearDown(self):
        self._lgpd._REGISTRY.clear()
        self._lgpd._REGISTRY.update(self._registry_original)

    def _make_cliente(self, nome='Cliente Registry Teste'):
        from clientes.models import Cliente
        return Cliente.objects.create(nome_razao_social=nome)

    def test_app_novo_registra_e_aparece_no_export_ca09(self):
        cliente = self._make_cliente()
        self._lgpd.registrar_exportador('app_teste', 'Seção Teste', lambda c: {'ok': True})

        self.assertIn('app_teste', self._lgpd.apps_registrados())

        secoes = self._lgpd.exportar_tudo(cliente)
        apps = [s['app'] for s in secoes]
        self.assertIn('app_teste', apps)
        secao_teste = next(s for s in secoes if s['app'] == 'app_teste')
        self.assertEqual(secao_teste['titulo'], 'Seção Teste')
        self.assertEqual(secao_teste['dados'], {'ok': True})

    def test_funcao_retornando_none_omite_secao(self):
        cliente = self._make_cliente('Cliente Sem Dado Nesse App')
        self._lgpd.registrar_exportador('app_vazio', 'Seção Vazia', lambda c: None)

        secoes = self._lgpd.exportar_tudo(cliente)
        apps = [s['app'] for s in secoes]
        self.assertNotIn('app_vazio', apps)

    def test_funcao_retornando_dict_vazio_omite_secao(self):
        cliente = self._make_cliente('Cliente Dict Vazio')
        self._lgpd.registrar_exportador('app_dict_vazio', 'Seção Dict Vazio', lambda c: {})

        secoes = self._lgpd.exportar_tudo(cliente)
        apps = [s['app'] for s in secoes]
        self.assertNotIn('app_dict_vazio', apps)

    def test_apps_de_negocio_reais_ja_registrados(self):
        # AppConfig.ready() dos apps de negocio ja rodou no boot do
        # processo de teste — clientes sempre se registra (RF-02).
        self.assertIn('clientes', self._lgpd.apps_registrados())

    def test_resumir_secoes_vazio(self):
        self.assertEqual(self._lgpd.resumir_secoes([]), 'sem dados em outros módulos')

    def test_resumir_secoes_com_lista(self):
        resumo = self._lgpd.resumir_secoes([
            {'app': 'financeiro', 'titulo': 'Financeiro', 'dados': {'receitas': [1, 2, 3]}},
        ])
        self.assertIn('financeiro:3', resumo)

    def test_formatar_em_linhas_dict_simples(self):
        linhas = self._lgpd.formatar_em_linhas({'nome': 'Fulano', 'idade': 30})
        self.assertIn('nome: Fulano', linhas)
        self.assertIn('idade: 30', linhas)

    def test_formatar_em_linhas_lista_de_dicts(self):
        linhas = self._lgpd.formatar_em_linhas({'itens': [{'descricao': 'Item A'}]})
        self.assertTrue(any('descricao: Item A' in l for l in linhas))
