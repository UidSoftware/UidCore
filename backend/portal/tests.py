"""Testes do app portal (Fase E.6 -- Manutencao #7).

Cobre RF-PO01 a RF-PO03 e RN-PO01 a RN-PO03 da Especificacao_Hotfix.md.
"""
import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from clientes.models import Cliente

from .lgpd import exportar_titular
from .models import AcessoPortalCliente

# Manutencao 72 (RF-07): teste que grava ImageField (User.foto) nunca
# grava no MEDIA_ROOT real do projeto -- diretorio temporario isolado,
# removido ao final da execucao do modulo (mesmo padrao de accounts/
# pagamentos/financeiro/administrativo).
_MEDIA_ROOT_TESTE = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(_MEDIA_ROOT_TESTE, ignore_errors=True)


def _jpeg_valido():
    buffer = io.BytesIO()
    Image.new('RGB', (40, 40), color='blue').save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.getvalue()


def _make_user(email='admin@teste.com'):
    return User.objects.create_user(email=email, password='senha123', nome_completo='Admin Teste')


def _make_cliente(nome='Cliente Teste'):
    return Cliente.objects.create(nome_razao_social=nome, tipo_pessoa='PJ')


class AcessoPortalClienteModelTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            email='cliente@teste.com', password='senha123', nome_completo='Cliente Usuario',
        )
        self.cliente = _make_cliente()

    def test_criar_acesso_rf_po01(self):
        acesso = AcessoPortalCliente.objects.create(usuario=self.usuario, cliente=self.cliente)
        self.assertTrue(acesso.is_active)

    def test_usuario_e_onetoone_rn_po01(self):
        AcessoPortalCliente.objects.create(usuario=self.usuario, cliente=self.cliente)
        outro_cliente = _make_cliente(nome='Outro Cliente')
        with self.assertRaises(Exception):
            AcessoPortalCliente.objects.create(usuario=self.usuario, cliente=outro_cliente)

    def test_herda_base_model_tem_is_active_e_created_at_rn_po03(self):
        acesso = AcessoPortalCliente.objects.create(usuario=self.usuario, cliente=self.cliente)
        self.assertTrue(hasattr(acesso, 'is_active'))
        self.assertTrue(hasattr(acesso, 'created_at'))
        self.assertTrue(acesso.is_active)


class AcessoPortalClienteAPITest(APITestCase):
    def setUp(self):
        self.admin = _make_user()
        self.client.force_authenticate(self.admin)
        self.cliente = _make_cliente()
        self.usuario_portal = User.objects.create_user(
            email='portal@teste.com', password='senha123', nome_completo='Usuario Portal',
        )

    def test_criar_acesso_via_api_rf_po01(self):
        resp = self.client.post('/api/v1/portal/acessos/', {
            'usuario': self.usuario_portal.id, 'cliente': self.cliente.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['usuario_email'], 'portal@teste.com')

    def test_destroy_faz_soft_delete_via_campo_ativo_rf_po02(self):
        acesso = AcessoPortalCliente.objects.create(usuario=self.usuario_portal, cliente=self.cliente)
        resp = self.client.delete(f'/api/v1/portal/acessos/{acesso.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        acesso.refresh_from_db()
        self.assertFalse(acesso.is_active)

    def test_listar_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/portal/acessos/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class AuditoriaManutencao62APITest(APITestCase):
    """Manutencao 62 — ciclo completo created_by/updated_by/deleted_by/deleted_at."""

    def test_ciclo_completo_auditoria_acesso_portal(self):
        user_a = _make_user(email='a62@teste.com')
        user_b = _make_user(email='b62@teste.com')
        user_c = _make_user(email='c62@teste.com')
        cliente = _make_cliente()
        usuario_portal = User.objects.create_user(
            email='portal62@teste.com', password='senha123', nome_completo='Usuario Portal 62',
        )

        self.client.force_authenticate(user_a)
        resp = self.client.post('/api/v1/portal/acessos/', {
            'usuario': usuario_portal.id, 'cliente': cliente.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        acesso_id = resp.data['id']
        acesso = AcessoPortalCliente.objects.get(pk=acesso_id)
        self.assertEqual(acesso.created_by, user_a)

        self.client.force_authenticate(user_b)
        resp = self.client.patch(f'/api/v1/portal/acessos/{acesso_id}/', {'ultimo_acesso': '2026-10-12T10:00:00Z'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        acesso.refresh_from_db()
        self.assertEqual(acesso.updated_by, user_b)
        self.assertEqual(acesso.created_by, user_a)

        self.client.force_authenticate(user_c)
        resp = self.client.delete(f'/api/v1/portal/acessos/{acesso_id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        acesso = AcessoPortalCliente.all_objects.get(pk=acesso_id)
        self.assertEqual(acesso.deleted_by, user_c)
        self.assertIsNotNone(acesso.deleted_at)
        self.assertFalse(AcessoPortalCliente.objects.filter(pk=acesso_id).exists())


@override_settings(MEDIA_ROOT=_MEDIA_ROOT_TESTE)
class ExportarTitularFotoUrlTest(TestCase):
    """Manutencao 72 (RF-07/RN-09) -- exportar_titular(cliente) passa a
    incluir foto_url de cada acesso, sem alterar as chaves preexistentes
    (usuario_email, ultimo_acesso) nem regredir o caso ja coberto (sem
    acesso -- None)."""

    def test_acesso_com_usuario_com_foto_inclui_foto_url(self):
        cliente = _make_cliente('Cliente LGPD Foto')
        usuario = User.objects.create_user(
            email='portal.foto.m72@teste.com', password='senha123', nome_completo='Usuario Portal Foto',
        )
        AcessoPortalCliente.objects.create(usuario=usuario, cliente=cliente)

        c = APIClient()
        c.force_authenticate(usuario)
        arquivo = SimpleUploadedFile('foto.jpg', _jpeg_valido(), content_type='image/jpeg')
        c.post('/api/v1/accounts/me/foto/', {'foto': arquivo}, format='multipart')

        resultado = exportar_titular(cliente)
        self.assertIsNotNone(resultado)
        item = resultado['acessos'][0]
        self.assertEqual(item['usuario_email'], 'portal.foto.m72@teste.com')
        self.assertIsNotNone(item['foto_url'])

    def test_acesso_com_usuario_sem_foto_e_none(self):
        cliente = _make_cliente('Cliente LGPD Sem Foto')
        usuario = User.objects.create_user(
            email='portal.semfoto.m72@teste.com', password='senha123', nome_completo='Usuario Sem Foto',
        )
        AcessoPortalCliente.objects.create(usuario=usuario, cliente=cliente)

        resultado = exportar_titular(cliente)
        self.assertIsNone(resultado['acessos'][0]['foto_url'])

    def test_cliente_sem_acesso_continua_retornando_none(self):
        cliente = _make_cliente('Cliente LGPD Sem Acesso')
        self.assertIsNone(exportar_titular(cliente))
