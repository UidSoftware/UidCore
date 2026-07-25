"""Testes do app administrativo (Fase E.3 -- Manutencao #7).

Cobre RF-A01 a RF-A02 e RN-A01 a RN-A03 da Especificacao_Hotfix.md.
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from clientes.models import Cliente

from .models import Documento, TipoDocumento


def _make_user(email='admin@teste.com'):
    return User.objects.create_user(email=email, password='senha123', nome_completo='Admin Teste')


class TipoDocumentoModelTest(TestCase):
    def test_criar_tipo_documento_rf_a01(self):
        tipo = TipoDocumento.objects.create(nome='Contrato Social')
        self.assertEqual(str(tipo), 'Contrato Social')

    def test_nome_unico(self):
        TipoDocumento.objects.create(nome='Contrato')
        with self.assertRaises(Exception):
            TipoDocumento.objects.create(nome='Contrato')


class DocumentoModelTest(TestCase):
    def setUp(self):
        self.tipo = TipoDocumento.objects.create(nome='Contrato')

    def test_cliente_e_opcional_rn_a02(self):
        doc = Documento.objects.create(
            titulo='Documento geral', tipo=self.tipo,
            arquivo=SimpleUploadedFile('doc.pdf', b'fake'),
        )
        self.assertIsNone(doc.cliente)

    def test_soft_delete_rn_a03(self):
        doc = Documento.objects.create(
            titulo='Documento X', tipo=self.tipo, arquivo=SimpleUploadedFile('doc2.pdf', b'fake'),
        )
        doc.is_active = False
        doc.save()
        self.assertTrue(Documento.objects.filter(pk=doc.pk).exists())


class DocumentoAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.tipo = TipoDocumento.objects.create(nome='Contrato')
        self.cliente = Cliente.objects.create(nome_razao_social='Cliente Teste', tipo_pessoa='PJ')

    def test_upload_documento_multipart_rn_a01(self):
        arquivo = SimpleUploadedFile('contrato.pdf', b'conteudo fake', content_type='application/pdf')
        resp = self.client.post('/api/v1/administrativo/documentos/', {
            'titulo': 'Contrato de Prestacao', 'tipo': self.tipo.id, 'arquivo': arquivo,
            'cliente': self.cliente.id,
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_documento_sem_cliente_e_valido(self):
        arquivo = SimpleUploadedFile('geral.pdf', b'conteudo fake', content_type='application/pdf')
        resp = self.client.post('/api/v1/administrativo/documentos/', {
            'titulo': 'Documento Geral', 'tipo': self.tipo.id, 'arquivo': arquivo,
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_destroy_faz_soft_delete_rn_a03(self):
        doc = Documento.objects.create(
            titulo='Del', tipo=self.tipo, arquivo=SimpleUploadedFile('del.pdf', b'fake'),
        )
        resp = self.client.delete(f'/api/v1/administrativo/documentos/{doc.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        doc.refresh_from_db()
        self.assertFalse(doc.is_active)

    def test_listar_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/administrativo/documentos/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class TipoDocumentoAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)

    def test_crud_tipos_rf_a01(self):
        resp = self.client.post('/api/v1/administrativo/tipos/', {'nome': 'Nota Fiscal'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        tipo_id = resp.data['id']

        resp = self.client.delete(f'/api/v1/administrativo/tipos/{tipo_id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        tipo = TipoDocumento.objects.get(pk=tipo_id)
        self.assertFalse(tipo.is_active)
