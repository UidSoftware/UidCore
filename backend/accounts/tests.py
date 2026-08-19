from unittest.mock import patch

from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from .models import User


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
