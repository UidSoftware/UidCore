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
