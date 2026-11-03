"""Relatar problema: o usuario do sistema abre um chamado que vira Manutencao no SystemD.

A chave fica so no backend (SYSTEMD_API_KEY) e identifica o sistema; sem ela o
recurso fica desligado e o botao nem aparece. O SystemD limita a 5 chamados/24h.
"""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

PRIORIDADES = ('BAIXA', 'MEDIA', 'ALTA')
TAMANHO_MAX_DESCRICAO = 2000
TIMEOUT_SEGUNDOS = 10


class RelatarProblemaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'ativo': bool(settings.SYSTEMD_API_KEY)})

    def post(self, request):
        if not settings.SYSTEMD_API_KEY:
            return Response({'erro': 'Relato de problema nao configurado neste sistema.'}, status=503)

        descricao = str(request.data.get('descricao') or '').strip()
        if not descricao:
            return Response({'descricao': 'Descreva o problema.'}, status=400)
        if len(descricao) > TAMANHO_MAX_DESCRICAO:
            return Response({'descricao': f'Use no maximo {TAMANHO_MAX_DESCRICAO} caracteres.'}, status=400)

        prioridade = str(request.data.get('prioridade') or 'MEDIA').strip().upper()
        if prioridade not in PRIORIDADES:
            return Response({'prioridade': 'Prioridade invalida.'}, status=400)

        corpo = json.dumps({
            'descricao': f'{descricao}\n\nRelatado em {settings.APP_NAME} por {request.user.email}.',
            'prioridade': prioridade,
        }).encode()
        chamada = urllib.request.Request(
            settings.SYSTEMD_API_URL,
            data=corpo,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'ApiKey {settings.SYSTEMD_API_KEY}',
            },
        )
        try:
            with urllib.request.urlopen(chamada, timeout=TIMEOUT_SEGUNDOS) as resposta:
                manutencao_id = json.loads(resposta.read()).get('manutencao_id')
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                return Response({'erro': 'Limite de chamados de hoje atingido. Fale com a Uid Software.'}, status=429)
            logger.error('SystemD recusou o relato de problema: HTTP %s', exc.code)
            return Response({'erro': 'Nao foi possivel enviar agora. Fale com a Uid Software.'}, status=502)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            logger.error('Falha ao enviar relato de problema: %s', exc.__class__.__name__)
            return Response({'erro': 'Nao foi possivel enviar agora. Tente de novo em instantes.'}, status=502)

        return Response({'mensagem': 'Problema enviado.', 'chamado': manutencao_id}, status=201)
