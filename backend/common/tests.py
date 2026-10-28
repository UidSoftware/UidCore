"""Testes de `common/permissions.py` — Manutencao 63 [NUCLEO 2/5] (RF-02/RF-09/CA-13).

Unitarios, sem HTTP real (request mockado via RequestFactory) — cobrem
IsFinanceiro, IsProfissional e BloqueiaEscritaDeProfissional isoladas,
nos dois sentidos (permite/bloqueia), conforme a tabela da secao 2.5 da
Especificacao_Hotfix.md. Os testes de integracao via API real (contas,
estornar, compras, agendamento, clientes) ficam nos apps respectivos.
"""
import io

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase, TestCase
from PIL import Image

from accounts.models import User
from common.media import LADO_PADRAO, TAMANHO_MAX_BYTES, processar_foto
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


def _jpeg_com_quadrante(exif_orientacao=None):
    """JPEG 40x40 com o quadrante superior-esquerdo (20x20) vermelho e o
    resto preto -- usado para confirmar visualmente que processar_foto
    corrige a orientacao (ImageOps.exif_transpose) ANTES de descartar o
    resto do bloco EXIF (RN-04). Com Orientation=6, o quadrante vermelho
    migra para o canto superior-direito apos a correcao (comportamento do
    Pillow confirmado empiricamente antes de escrever este teste)."""
    imagem = Image.new('RGB', (40, 40), color='black')
    for y in range(20):
        for x in range(20):
            imagem.putpixel((x, y), (255, 0, 0))
    buffer = io.BytesIO()
    if exif_orientacao is not None:
        exif = imagem.getexif()
        exif[274] = exif_orientacao  # tag Orientation
        imagem.save(buffer, format='JPEG', quality=95, exif=exif)
    else:
        imagem.save(buffer, format='JPEG', quality=95)
    buffer.seek(0)
    return buffer.getvalue()


def _upload(conteudo, nome='foto.jpg', content_type='image/jpeg'):
    return SimpleUploadedFile(nome, conteudo, content_type=content_type)


class ProcessarFotoTest(SimpleTestCase):
    """Manutencao 72 (RF-05) -- common/media.py::processar_foto. Unitario
    e sem banco (SimpleTestCase): a funcao nao toca em nenhum model (RN-08
    -- zero acoplamento com accounts/clientes/rh)."""

    def test_recorta_quadrado_e_redimensiona_para_webp_rf05(self):
        conteudo = processar_foto(_upload(_jpeg_com_quadrante()))
        imagem = Image.open(conteudo)
        self.assertEqual(imagem.size, (LADO_PADRAO, LADO_PADRAO))
        self.assertEqual(imagem.format, 'WEBP')

    def test_remove_todo_exif_inclusive_sem_orientacao_rn04(self):
        conteudo = processar_foto(_upload(_jpeg_com_quadrante()))
        imagem = Image.open(conteudo)
        self.assertFalse(dict(imagem.getexif()))

    def test_remove_todo_exif_apos_orientacao_com_rotacao_rn04(self):
        conteudo = processar_foto(_upload(_jpeg_com_quadrante(exif_orientacao=6)))
        imagem = Image.open(conteudo)
        self.assertFalse(dict(imagem.getexif()))

    def test_corrige_orientacao_antes_de_descartar_exif_rn04(self):
        conteudo = processar_foto(_upload(_jpeg_com_quadrante(exif_orientacao=6)))
        imagem = Image.open(conteudo).convert('RGB')
        lado = imagem.size[0]
        canto_superior_direito = imagem.getpixel((lado - 5, 5))
        canto_superior_esquerdo = imagem.getpixel((5, 5))
        self.assertGreater(canto_superior_direito[0], 150)  # vermelho migrou p/ direita
        self.assertLess(canto_superior_esquerdo[0], 100)  # esquerda ficou preta

    def test_arquivo_maior_que_5mb_e_rejeitado_sem_decodificar_rn02(self):
        conteudo_grande = b'0' * (TAMANHO_MAX_BYTES + 1)
        with self.assertRaises(ValidationError):
            processar_foto(_upload(conteudo_grande, nome='grande.jpg'))

    def test_arquivo_que_nao_e_imagem_de_verdade_e_rejeitado_rn03(self):
        pdf_renomeado = _upload(b'%PDF-1.4 conteudo fake de pdf, nunca uma imagem real',
                                 nome='documento.jpg', content_type='image/jpeg')
        with self.assertRaises(ValidationError):
            processar_foto(pdf_renomeado)

    def test_nome_final_e_sempre_uuid_webp_rn05(self):
        conteudo = processar_foto(_upload(_jpeg_com_quadrante(), nome='nome_original_do_usuario.jpg'))
        self.assertTrue(conteudo.name.endswith('.webp'))
        self.assertNotIn('nome_original', conteudo.name)
        self.assertNotIn('usuario', conteudo.name)
