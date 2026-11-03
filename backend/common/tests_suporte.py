"""Relatar problema -> Manutencao no SystemD (chamada HTTP mockada)."""
import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import User

URL = '/api/v1/suporte/relatar-problema/'
CHAVE = 'chave-de-teste'


def _resposta(corpo):
    r = MagicMock()
    r.read.return_value = json.dumps(corpo).encode()
    r.__enter__.return_value = r
    return r


class RelatarProblemaTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='cliente@teste.com', password='senha123', nome_completo='Cliente', perfil='OPERACIONAL',
        )
        self.client.force_authenticate(self.user)

    def test_sem_login_401(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(URL).status_code, 401)

    @override_settings(SYSTEMD_API_KEY='')
    def test_sem_chave_fica_desligado_e_nao_chama_o_systemd(self):
        self.assertEqual(self.client.get(URL).json(), {'ativo': False})
        with patch('common.suporte.urllib.request.urlopen') as urlopen:
            resp = self.client.post(URL, {'descricao': 'Tela quebrada'}, format='json')
        self.assertEqual(resp.status_code, 503)
        urlopen.assert_not_called()

    @override_settings(SYSTEMD_API_KEY=CHAVE, APP_NAME='LojaTeste', SYSTEMD_API_URL='https://systemd.test/x/')
    def test_envia_com_a_chave_e_identifica_quem_relatou(self):
        self.assertEqual(self.client.get(URL).json(), {'ativo': True})
        with patch('common.suporte.urllib.request.urlopen', return_value=_resposta({'manutencao_id': 42})) as urlopen:
            resp = self.client.post(URL, {'descricao': 'Tela quebrada', 'prioridade': 'alta'}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['chamado'], 42)
        chamada = urlopen.call_args[0][0]
        self.assertEqual(chamada.full_url, 'https://systemd.test/x/')
        self.assertEqual(chamada.get_header('Authorization'), f'ApiKey {CHAVE}')
        corpo = json.loads(chamada.data)
        self.assertEqual(corpo['prioridade'], 'ALTA')
        self.assertIn('Tela quebrada', corpo['descricao'])
        self.assertIn('LojaTeste', corpo['descricao'])
        self.assertIn('cliente@teste.com', corpo['descricao'])
        self.assertNotIn(CHAVE, json.dumps(resp.json()))

    @override_settings(SYSTEMD_API_KEY=CHAVE)
    def test_valida_descricao_e_prioridade(self):
        with patch('common.suporte.urllib.request.urlopen') as urlopen:
            self.assertEqual(self.client.post(URL, {'descricao': '  '}, format='json').status_code, 400)
            self.assertEqual(self.client.post(URL, {'descricao': 'x' * 2001}, format='json').status_code, 400)
            self.assertEqual(self.client.post(URL, {'descricao': 'ok', 'prioridade': 'URGENTE'}, format='json').status_code, 400)
        urlopen.assert_not_called()

    @override_settings(SYSTEMD_API_KEY=CHAVE)
    def test_erros_do_systemd_nao_vazam_detalhe(self):
        def http(code):
            return urllib.error.HTTPError('https://x', code, 'erro', {}, io.BytesIO(b'{"erro":"interno"}'))
        for excecao, esperado in [
            (http(429), 429), (http(403), 502), (urllib.error.URLError('dns'), 502), (TimeoutError(), 502),
        ]:
            with patch('common.suporte.urllib.request.urlopen', side_effect=excecao):
                resp = self.client.post(URL, {'descricao': 'Falhou'}, format='json')
            self.assertEqual(resp.status_code, esperado)
            self.assertNotIn('interno', json.dumps(resp.json()))
