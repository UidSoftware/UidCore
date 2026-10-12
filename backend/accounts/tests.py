import importlib
from unittest.mock import patch

from django.apps import apps as django_apps
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from .models import PerfilUsuario, User


class AlterarSenhaViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='u1@x.com', password='SenhaAtual1', nome_completo='Usuario 1',
        )

    def test_troca_senha_com_sucesso(self):
        c = APIClient()
        c.force_authenticate(self.user)
        r = c.post('/api/v1/accounts/alterar-senha/', {
            'senha_atual': 'SenhaAtual1', 'senha_nova': 'SenhaNova1',
        })
        self.assertEqual(r.status_code, 200, r.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('SenhaNova1'))

    def test_senha_atual_errada_e_rejeitada(self):
        c = APIClient()
        c.force_authenticate(self.user)
        r = c.post('/api/v1/accounts/alterar-senha/', {
            'senha_atual': 'errada', 'senha_nova': 'SenhaNova1',
        })
        self.assertEqual(r.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('SenhaAtual1'))

    def test_senha_curta_e_rejeitada(self):
        c = APIClient()
        c.force_authenticate(self.user)
        r = c.post('/api/v1/accounts/alterar-senha/', {
            'senha_atual': 'SenhaAtual1', 'senha_nova': '123',
        })
        self.assertEqual(r.status_code, 400)

    def test_sem_autenticacao_e_rejeitado(self):
        c = APIClient()
        r = c.post('/api/v1/accounts/alterar-senha/', {
            'senha_atual': 'SenhaAtual1', 'senha_nova': 'SenhaNova1',
        })
        self.assertEqual(r.status_code, 401)


class SolicitarAcessoViewTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='adm@x.com', password='x', nome_completo='Admin', is_staff=True,
        )
        self.comum = User.objects.create_user(
            email='comum@x.com', password='x', nome_completo='Comum', is_staff=False,
        )
        self.alvo = User.objects.create_user(
            email='alvo@x.com', password='x', nome_completo='Alvo',
        )

    @patch('accounts.services.enviar_email_sistema')
    def test_admin_envia_acesso(self, mock_enviar):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.post('/api/v1/accounts/solicitar-acesso/', {'usuario_id': self.alvo.id})
        self.assertEqual(r.status_code, 200, r.content)
        mock_enviar.assert_called_once()
        destinatario = mock_enviar.call_args[0][0]
        self.assertEqual(destinatario, 'alvo@x.com')

    def test_nao_staff_bloqueado(self):
        c = APIClient()
        c.force_authenticate(self.comum)
        r = c.post('/api/v1/accounts/solicitar-acesso/', {'usuario_id': self.alvo.id})
        self.assertEqual(r.status_code, 403)

    @patch('accounts.services.enviar_email_sistema')
    def test_usuario_inexistente_404(self, mock_enviar):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.post('/api/v1/accounts/solicitar-acesso/', {'usuario_id': 999999})
        self.assertEqual(r.status_code, 404)
        mock_enviar.assert_not_called()


class DefinirSenhaViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='u2@x.com', password='SenhaVelha1', nome_completo='Usuario 2',
        )

    def _link_valido(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        return uid, token

    def test_define_senha_com_token_valido(self):
        uid, token = self._link_valido()
        c = APIClient()
        r = c.post('/api/v1/accounts/definir-senha/', {
            'uid': uid, 'token': token, 'senha': 'SenhaNovaDefinida1',
        })
        self.assertEqual(r.status_code, 200, r.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('SenhaNovaDefinida1'))

    def test_token_invalido_e_rejeitado(self):
        uid, _ = self._link_valido()
        c = APIClient()
        r = c.post('/api/v1/accounts/definir-senha/', {
            'uid': uid, 'token': 'token-invalido', 'senha': 'SenhaNovaDefinida1',
        })
        self.assertEqual(r.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('SenhaVelha1'))

    def test_token_usado_uma_vez_nao_funciona_de_novo(self):
        """Trocar a senha muda o hash usado no token -> reuso do mesmo link falha (RN de seguranca)."""
        uid, token = self._link_valido()
        c = APIClient()
        r1 = c.post('/api/v1/accounts/definir-senha/', {
            'uid': uid, 'token': token, 'senha': 'PrimeiraTroca1',
        })
        self.assertEqual(r1.status_code, 200)

        r2 = c.post('/api/v1/accounts/definir-senha/', {
            'uid': uid, 'token': token, 'senha': 'SegundaTroca1',
        })
        self.assertEqual(r2.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('PrimeiraTroca1'))


class UserViewSetTest(TestCase):
    """Manutencao #44 -- tela de Usuarios (IsAdmin): CRUD so para is_staff."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin.uv44@teste.com', password='x', nome_completo='Admin UV', is_staff=True,
        )
        self.comum = User.objects.create_user(
            email='comum.uv44@teste.com', password='x', nome_completo='Comum UV', is_staff=False,
        )

    def test_list_por_admin_ok(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.get('/api/v1/accounts/usuarios/')
        self.assertEqual(r.status_code, 200, r.content)

    def test_list_por_nao_staff_403(self):
        c = APIClient()
        c.force_authenticate(self.comum)
        r = c.get('/api/v1/accounts/usuarios/')
        self.assertEqual(r.status_code, 403)

    def test_list_sem_autenticacao_401(self):
        c = APIClient()
        r = c.get('/api/v1/accounts/usuarios/')
        self.assertEqual(r.status_code, 401)

    def test_create_por_admin_senha_vazia_gera_unusable_password(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.post('/api/v1/accounts/usuarios/', {
            'email': 'novo.uv44@teste.com', 'nome_completo': 'Novo Usuario',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        novo = User.objects.get(email='novo.uv44@teste.com')
        self.assertFalse(novo.has_usable_password())

    def test_create_por_admin_com_senha(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.post('/api/v1/accounts/usuarios/', {
            'email': 'novosenha.uv44@teste.com', 'nome_completo': 'Novo Com Senha',
            'password': 'SenhaValida1',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        novo = User.objects.get(email='novosenha.uv44@teste.com')
        self.assertTrue(novo.check_password('SenhaValida1'))

    def test_create_por_nao_staff_403_zero_registros(self):
        c = APIClient()
        c.force_authenticate(self.comum)
        r = c.post('/api/v1/accounts/usuarios/', {
            'email': 'bloqueado.uv44@teste.com', 'nome_completo': 'Bloqueado',
        }, format='json')
        self.assertEqual(r.status_code, 403)
        self.assertFalse(User.objects.filter(email='bloqueado.uv44@teste.com').exists())

    def test_update_com_senha_muda_hash(self):
        alvo = User.objects.create_user(
            email='alvo.uv44@teste.com', password='SenhaOriginal1', nome_completo='Alvo UV',
        )
        hash_antes = alvo.password
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.patch(f'/api/v1/accounts/usuarios/{alvo.id}/', {'password': 'SenhaNovaUV1'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        alvo.refresh_from_db()
        self.assertNotEqual(alvo.password, hash_antes)
        self.assertTrue(alvo.check_password('SenhaNovaUV1'))

    def test_destroy_faz_soft_disable(self):
        alvo = User.objects.create_user(
            email='desativar.uv44@teste.com', password='x', nome_completo='Desativar',
        )
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.delete(f'/api/v1/accounts/usuarios/{alvo.id}/')
        self.assertEqual(r.status_code, 204)
        alvo.refresh_from_db()
        self.assertFalse(alvo.is_active)
        self.assertTrue(User.objects.filter(pk=alvo.id).exists())

    def test_destroy_por_nao_staff_403(self):
        alvo = User.objects.create_user(
            email='naomexer.uv44@teste.com', password='x', nome_completo='Nao Mexer',
        )
        c = APIClient()
        c.force_authenticate(self.comum)
        r = c.delete(f'/api/v1/accounts/usuarios/{alvo.id}/')
        self.assertEqual(r.status_code, 403)
        alvo.refresh_from_db()
        self.assertTrue(alvo.is_active)

    def test_search_filter_por_email_e_nome(self):
        User.objects.create_user(
            email='buscavel.uv44@teste.com', password='x', nome_completo='Fulano Buscavel',
        )
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.get('/api/v1/accounts/usuarios/?search=Buscavel')
        self.assertEqual(r.status_code, 200, r.content)
        emails = [u['email'] for u in r.data['results']]
        self.assertIn('buscavel.uv44@teste.com', emails)


# ---------------------------------------------------------------------------
# Manutencao #60 -- PerfilUsuario.SUPERADMIN + User.tem_acesso_total (RBAC)
# ---------------------------------------------------------------------------

class PerfilUsuarioSuperadminChoiceTest(TestCase):
    """CA-01 -- SUPERADMIN existe nas choices do campo perfil."""

    def test_superadmin_esta_nas_choices(self):
        valores = [valor for valor, _ in PerfilUsuario.choices]
        self.assertIn('SUPERADMIN', valores)
        self.assertEqual(PerfilUsuario.SUPERADMIN, 'SUPERADMIN')


class TemAcessoTotalPropertyTest(TestCase):
    """CA-02 a CA-05 -- User.tem_acesso_total (RF-02/RN-01)."""

    def test_operacional_sem_is_staff_nao_tem_acesso_total(self):
        u = User.objects.create_user(
            email='op.m60@teste.com', password='x', nome_completo='Operacional',
            perfil='OPERACIONAL', is_staff=False,
        )
        self.assertFalse(u.tem_acesso_total)

    def test_admin_sem_is_staff_tem_acesso_total(self):
        u = User.objects.create_user(
            email='adm.m60@teste.com', password='x', nome_completo='Admin',
            perfil='ADMIN', is_staff=False,
        )
        self.assertTrue(u.tem_acesso_total)

    def test_superadmin_sem_is_staff_tem_acesso_total(self):
        u = User.objects.create_user(
            email='super.m60@teste.com', password='x', nome_completo='Super',
            perfil='SUPERADMIN', is_staff=False,
        )
        self.assertTrue(u.tem_acesso_total)

    def test_is_staff_true_com_perfil_operacional_tem_acesso_total_retrocompat(self):
        """RN-01: is_staff=True concede acesso total independente do perfil."""
        u = User.objects.create_user(
            email='legado.m60@teste.com', password='x', nome_completo='Legado',
            perfil='OPERACIONAL', is_staff=True,
        )
        self.assertTrue(u.tem_acesso_total)


class IsAdminViaPerfilOuIsStaffAPITest(TestCase):
    """CA-06 -- endpoint protegido por IsAdmin (accounts/usuarios) responde
    403 para tem_acesso_total=False e 200 para tem_acesso_total=True, tanto
    via perfil quanto via is_staff."""

    def test_403_para_operacional_sem_is_staff(self):
        u = User.objects.create_user(
            email='op.m60b@teste.com', password='x', nome_completo='Operacional',
            perfil='OPERACIONAL', is_staff=False,
        )
        c = APIClient()
        c.force_authenticate(u)
        r = c.get('/api/v1/accounts/usuarios/')
        self.assertEqual(r.status_code, 403)

    def test_200_via_perfil_admin_sem_is_staff(self):
        u = User.objects.create_user(
            email='adm.m60b@teste.com', password='x', nome_completo='Admin',
            perfil='ADMIN', is_staff=False,
        )
        c = APIClient()
        c.force_authenticate(u)
        r = c.get('/api/v1/accounts/usuarios/')
        self.assertEqual(r.status_code, 200, r.content)

    def test_200_via_is_staff_com_perfil_operacional(self):
        u = User.objects.create_user(
            email='staff.m60b@teste.com', password='x', nome_completo='Staff Legado',
            perfil='OPERACIONAL', is_staff=True,
        )
        c = APIClient()
        c.force_authenticate(u)
        r = c.get('/api/v1/accounts/usuarios/')
        self.assertEqual(r.status_code, 200, r.content)


class UserAdminSerializerFieldsTest(TestCase):
    """CA-09 -- UserAdminSerializer nao expoe mais is_staff; expoe tem_acesso_total."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin.m60c@teste.com', password='x', nome_completo='Admin', perfil='ADMIN', is_staff=False,
        )

    def test_list_nao_expoe_is_staff_e_expoe_tem_acesso_total(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.get('/api/v1/accounts/usuarios/')
        self.assertEqual(r.status_code, 200, r.content)
        item = next(u for u in r.data['results'] if u['email'] == self.admin.email)
        self.assertNotIn('is_staff', item)
        self.assertIn('tem_acesso_total', item)
        self.assertTrue(item['tem_acesso_total'])

    def test_create_response_nao_expoe_is_staff(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.post('/api/v1/accounts/usuarios/', {
            'email': 'novo.m60c@teste.com', 'nome_completo': 'Novo', 'perfil': 'OPERACIONAL',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertNotIn('is_staff', r.data)
        self.assertIn('tem_acesso_total', r.data)

    def test_patch_com_is_staff_no_payload_e_ignorado_sem_erro(self):
        """is_staff deixou de ser campo do serializer -- enviar no payload
        nao quebra a request nem altera o campo real (nao esta mais em
        fields, DRF ignora silenciosamente)."""
        alvo = User.objects.create_user(
            email='alvo.m60c@teste.com', password='x', nome_completo='Alvo', perfil='OPERACIONAL', is_staff=False,
        )
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.patch(f'/api/v1/accounts/usuarios/{alvo.id}/', {'is_staff': True}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        alvo.refresh_from_db()
        self.assertFalse(alvo.is_staff)


class UserSerializerMeEndpointTest(TestCase):
    """CA-10 -- UserSerializer (/me/) expoe tem_acesso_total calculado."""

    def test_me_expoe_tem_acesso_total_true_para_admin(self):
        u = User.objects.create_user(
            email='meadmin.m60@teste.com', password='x', nome_completo='Me Admin', perfil='ADMIN', is_staff=False,
        )
        c = APIClient()
        c.force_authenticate(u)
        r = c.get('/api/v1/accounts/me/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.data['tem_acesso_total'])

    def test_me_expoe_tem_acesso_total_false_para_operacional(self):
        u = User.objects.create_user(
            email='meop.m60@teste.com', password='x', nome_completo='Me Op', perfil='OPERACIONAL', is_staff=False,
        )
        c = APIClient()
        c.force_authenticate(u)
        r = c.get('/api/v1/accounts/me/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(r.data['tem_acesso_total'])


class SuperadminPromocaoValidationAPITest(TestCase):
    """CA-11/CA-12 -- so SUPERADMIN pode atribuir perfil=SUPERADMIN (RF-06/RN-02)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin.m60d@teste.com', password='x', nome_completo='Admin', perfil='ADMIN', is_staff=False,
        )
        self.superadmin = User.objects.create_user(
            email='super.m60d@teste.com', password='x', nome_completo='Super', perfil='SUPERADMIN', is_staff=False,
        )

    def test_admin_nao_pode_criar_usuario_com_perfil_superadmin(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        antes = User.objects.count()
        r = c.post('/api/v1/accounts/usuarios/', {
            'email': 'tentativa.m60d@teste.com', 'nome_completo': 'Tentativa', 'perfil': 'SUPERADMIN',
        }, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn('perfil', r.data)
        self.assertEqual(User.objects.count(), antes)

    def test_admin_nao_pode_promover_terceiro_para_superadmin_via_patch(self):
        alvo = User.objects.create_user(
            email='alvo.m60d@teste.com', password='x', nome_completo='Alvo', perfil='OPERACIONAL', is_staff=False,
        )
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.patch(f'/api/v1/accounts/usuarios/{alvo.id}/', {'perfil': 'SUPERADMIN'}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        alvo.refresh_from_db()
        self.assertEqual(alvo.perfil, 'OPERACIONAL')

    def test_superadmin_pode_criar_usuario_com_perfil_superadmin(self):
        c = APIClient()
        c.force_authenticate(self.superadmin)
        r = c.post('/api/v1/accounts/usuarios/', {
            'email': 'novosuper.m60d@teste.com', 'nome_completo': 'Novo Super', 'perfil': 'SUPERADMIN',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        novo = User.objects.get(email='novosuper.m60d@teste.com')
        self.assertEqual(novo.perfil, 'SUPERADMIN')

    def test_superadmin_pode_promover_terceiro_via_patch(self):
        alvo = User.objects.create_user(
            email='alvo2.m60d@teste.com', password='x', nome_completo='Alvo2', perfil='OPERACIONAL', is_staff=False,
        )
        c = APIClient()
        c.force_authenticate(self.superadmin)
        r = c.patch(f'/api/v1/accounts/usuarios/{alvo.id}/', {'perfil': 'SUPERADMIN'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        alvo.refresh_from_db()
        self.assertEqual(alvo.perfil, 'SUPERADMIN')


class SuperadminEdicaoProtegidaAPITest(TestCase):
    """CA-13/CA-14/CA-15 -- so SUPERADMIN edita/desativa conta SUPERADMIN
    (RF-07/RN-03); leitura continua liberada para qualquer IsAdmin (RN-04)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin.m60e@teste.com', password='x', nome_completo='Admin', perfil='ADMIN', is_staff=False,
        )
        self.superadmin = User.objects.create_user(
            email='super.m60e@teste.com', password='x', nome_completo='Super', perfil='SUPERADMIN', is_staff=False,
        )
        self.outro_superadmin = User.objects.create_user(
            email='super2.m60e@teste.com', password='x', nome_completo='Super2', perfil='SUPERADMIN', is_staff=False,
        )

    def test_admin_nao_pode_editar_conta_superadmin(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.patch(f'/api/v1/accounts/usuarios/{self.superadmin.id}/', {'nome_completo': 'Hackeado'}, format='json')
        self.assertEqual(r.status_code, 403, r.content)
        self.superadmin.refresh_from_db()
        self.assertEqual(self.superadmin.nome_completo, 'Super')

    def test_admin_nao_pode_desativar_conta_superadmin(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.delete(f'/api/v1/accounts/usuarios/{self.superadmin.id}/')
        self.assertEqual(r.status_code, 403, r.content)
        self.superadmin.refresh_from_db()
        self.assertTrue(self.superadmin.is_active)

    def test_superadmin_pode_editar_outra_conta_superadmin(self):
        c = APIClient()
        c.force_authenticate(self.superadmin)
        r = c.patch(f'/api/v1/accounts/usuarios/{self.outro_superadmin.id}/', {'nome_completo': 'Editado'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.outro_superadmin.refresh_from_db()
        self.assertEqual(self.outro_superadmin.nome_completo, 'Editado')

    def test_superadmin_pode_autoeditar(self):
        c = APIClient()
        c.force_authenticate(self.superadmin)
        r = c.patch(f'/api/v1/accounts/usuarios/{self.superadmin.id}/', {'nome_completo': 'Eu Mesmo'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)

    def test_superadmin_pode_desativar_outra_conta_superadmin(self):
        c = APIClient()
        c.force_authenticate(self.superadmin)
        r = c.delete(f'/api/v1/accounts/usuarios/{self.outro_superadmin.id}/')
        self.assertEqual(r.status_code, 204, r.content)
        self.outro_superadmin.refresh_from_db()
        self.assertFalse(self.outro_superadmin.is_active)

    def test_admin_pode_ler_lista_com_contas_superadmin(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.get('/api/v1/accounts/usuarios/')
        self.assertEqual(r.status_code, 200, r.content)
        emails = [u['email'] for u in r.data['results']]
        self.assertIn(self.superadmin.email, emails)

    def test_admin_pode_ler_detalhe_de_conta_superadmin(self):
        c = APIClient()
        c.force_authenticate(self.admin)
        r = c.get(f'/api/v1/accounts/usuarios/{self.superadmin.id}/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data['email'], self.superadmin.email)


class SeedSuperadminMigrationTest(TestCase):
    """CA-16/CA-17/CA-18 -- migration 0004_seed_superadmin_perfil (RF-13/RN-06).

    Chama a funcao RunPython diretamente contra os models reais (mesma
    logica de producao) em vez de rodar o framework de migrations inteiro
    -- suficiente para validar a regra de dado em si.
    """

    def _seed_superadmin(self):
        mod = importlib.import_module('accounts.migrations.0004_seed_superadmin_perfil')
        mod.seed_superadmin(django_apps, None)

    def test_promove_is_staff_e_superuser_para_superadmin(self):
        legado = User.objects.create_user(
            email='legado.m60mig@teste.com', password='x', nome_completo='Legado',
        )
        legado.is_staff = True
        legado.is_superuser = True
        legado.save(update_fields=['is_staff', 'is_superuser'])

        self._seed_superadmin()

        legado.refresh_from_db()
        self.assertEqual(legado.perfil, 'SUPERADMIN')

    def test_nao_promove_staff_sem_superuser(self):
        so_staff = User.objects.create_user(
            email='sostaff.m60mig@teste.com', password='x', nome_completo='So Staff', is_staff=True,
        )
        self._seed_superadmin()
        so_staff.refresh_from_db()
        self.assertNotEqual(so_staff.perfil, 'SUPERADMIN')

    def test_conta_especifica_e_forcada_para_admin_sem_staff(self):
        conta = User.objects.create_user(
            email='editoresdesucessos@gmail.com', password='x', nome_completo='Editores',
        )
        conta.is_staff = True
        conta.is_superuser = True
        conta.save(update_fields=['is_staff', 'is_superuser'])

        self._seed_superadmin()

        conta.refresh_from_db()
        self.assertEqual(conta.perfil, 'ADMIN')
        self.assertFalse(conta.is_staff)

    def test_migration_idempotente_sem_conta_especifica_nao_falha(self):
        """CA-18: base sem editoresdesucessos@gmail.com (ambiente de
        teste/CI) -- rodar a funcao (inclusive 2x) nao pode lancar excecao."""
        User.objects.create_user(email='qualquer.m60mig@teste.com', password='x', nome_completo='Qualquer')
        self._seed_superadmin()
        self._seed_superadmin()  # idempotente -- rodar de novo nao altera nem falha


class PermissaoNovosPerfisUsuariosAPITest(TestCase):
    """Manutencao 63 [NUCLEO 2/5] (RF-09) -- UserViewSet permanece IsAdmin
    puro: nem FINANCEIRO nem PROFISSIONAL entram no OR de IsAdmin, 403
    automatico sem mudanca de codigo em accounts/views.py (CA-04/CA-09)."""

    def test_financeiro_sem_acesso_usuarios(self):
        u = User.objects.create_user(
            email='financeiro.m63@teste.com', password='x', nome_completo='Financeiro',
            perfil='FINANCEIRO', is_staff=False,
        )
        c = APIClient()
        c.force_authenticate(u)
        r = c.get('/api/v1/accounts/usuarios/')
        self.assertEqual(r.status_code, 403)

    def test_profissional_sem_acesso_usuarios(self):
        u = User.objects.create_user(
            email='profissional.m63@teste.com', password='x', nome_completo='Profissional',
            perfil='PROFISSIONAL', is_staff=False,
        )
        c = APIClient()
        c.force_authenticate(u)
        r = c.get('/api/v1/accounts/usuarios/')
        self.assertEqual(r.status_code, 403)
