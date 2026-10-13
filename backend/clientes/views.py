from django.db import transaction
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from common.lgpd import exportar_tudo, formatar_em_linhas, resumir_secoes
from common.mixins import AuditMixin
from common.models import ExportacaoTitular, FormatoExportacao
from common.permissions import BloqueiaEscritaDeProfissional, IsAdmin

from .models import AcionistaCliente, Cliente, HistoricoCliente
from .serializers import AcionistaClienteSerializer, ClienteSerializer, HistoricoClienteSerializer


class ClienteViewSet(AuditMixin, viewsets.ModelViewSet):
    serializer_class = ClienteSerializer
    permission_classes = [BloqueiaEscritaDeProfissional]  # Manutencao 63 (RF-06) — era implicito (IsAuthenticated)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nome_razao_social', 'documento', 'email', 'cidade']
    ordering_fields = ['nome_razao_social', 'created_at', 'segmento']
    ordering = ['-created_at']

    def get_queryset(self):
        return Cliente.objects.filter(is_active=True).prefetch_related('historico', 'acionistas')

    def get_permissions(self):
        # Manutencao #66 [NUCLEO 5/5] — RF-05/RF-06/RN-01: exportar e
        # anonimizar dados do titular exigem tem_acesso_total, diferente
        # da permissao padrao da viewset (BloqueiaEscritaDeProfissional),
        # que libera LEITURA pra qualquer perfil autenticado. Dado de
        # titular completo (ou a eliminacao dele) nao e leitura comum.
        if self.action in ('exportar', 'anonimizar'):
            return [IsAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=['get'], url_path='exportar')
    def exportar(self, request, pk=None):
        cliente = self.get_object()
        formato = (request.query_params.get('formato') or 'json').lower()
        if formato not in ('json', 'pdf'):
            return Response(
                {'detail': 'Formato inválido — use formato=json ou formato=pdf.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        secoes = exportar_tudo(cliente)

        # RF-05: registra a exportação ANTES de devolver a resposta — é o
        # "backup" exigido pela anonimização (RN-02). Se a geracao do
        # PDF falhar depois, o registro ja existir e so rastro de
        # tentativa (aceitavel, pior seria o inverso).
        ExportacaoTitular.objects.create(
            cliente=cliente,
            formato=FormatoExportacao.JSON if formato == 'json' else FormatoExportacao.PDF,
            conteudo_resumo=resumir_secoes(secoes),
            created_by=request.user,
        )

        data_emissao = timezone.now()
        cliente_capa = {
            'nome_razao_social': cliente.nome_razao_social,
            'documento': cliente.documento,
            'tipo_pessoa': cliente.get_tipo_pessoa_display(),
        }

        if formato == 'json':
            return Response({
                'cliente': cliente_capa,
                'data_emissao': data_emissao.isoformat(),
                'secoes': secoes,
            })

        # formato == 'pdf'
        from weasyprint import HTML

        secoes_pdf = [
            {'titulo': secao['titulo'], 'linhas': formatar_em_linhas(secao['dados'])}
            for secao in secoes
        ]
        html = render_to_string('lgpd/exportacao_titular.html', {
            'cliente': cliente_capa,
            'data_emissao': data_emissao.strftime('%d/%m/%Y %H:%M'),
            'secoes': secoes_pdf,
        })
        pdf_bytes = HTML(string=html).write_pdf()
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="titular_{cliente.id}.pdf"'
        return response

    @action(detail=True, methods=['post'], url_path='anonimizar')
    def anonimizar(self, request, pk=None):
        cliente = self.get_object()

        if request.data.get('confirmo') is not True:
            return Response(
                {'detail': 'Confirmação obrigatória — envie {"confirmo": true}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not ExportacaoTitular.objects.filter(cliente=cliente).exists():
            return Response(
                {'detail': 'É necessário exportar os dados do titular antes de anonimizar '
                            '(RN-02 — a exportação é o backup exigido antes da eliminação).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cliente.anonimizado:
            return Response(
                {'detail': 'Este cliente já foi anonimizado anteriormente — operação não se repete.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            cliente.nome_razao_social = f'Titular anonimizado #{cliente.id}'
            cliente.documento = None
            cliente.cpf = ''
            cliente.cnpj = ''
            cliente.telefone = ''
            cliente.email = ''
            cliente.endereco = ''
            cliente.cidade = ''
            cliente.estado = ''
            cliente.cep = ''
            cliente.observacoes = ''
            cliente.data_nascimento = None
            cliente.anonimizado = True
            cliente.anonimizado_em = timezone.now()
            cliente.anonimizado_por = request.user
            cliente.save()

            HistoricoCliente.objects.filter(cliente=cliente).update(
                descricao='[conteúdo removido por anonimização LGPD]'
            )

            for acionista in AcionistaCliente.objects.filter(cliente=cliente):
                acionista.nome = f'Acionista anonimizado #{acionista.pk}'
                acionista.email = ''
                acionista.cpf = ''
                acionista.telefone = ''
                acionista.whatsapp = ''
                acionista.save()

        serializer = self.get_serializer(cliente)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='historico')
    def adicionar_historico(self, request, pk=None):
        cliente = self.get_object()
        serializer = HistoricoClienteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(cliente=cliente)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'], url_path='acionistas')
    def acionistas(self, request, pk=None):
        cliente = self.get_object()
        if request.method == 'GET':
            qs = AcionistaCliente.objects.filter(cliente=cliente, is_active=True)
            return Response(AcionistaClienteSerializer(qs, many=True).data)
        serializer = AcionistaClienteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(cliente=cliente)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'acionistas/(?P<acid>\d+)')
    def acionista_detalhe(self, request, pk=None, acid=None):
        cliente = self.get_object()
        try:
            acionista = AcionistaCliente.objects.get(pk=acid, cliente=cliente, is_active=True)
        except AcionistaCliente.DoesNotExist:
            return Response({'detail': 'Acionista não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'DELETE':
            acionista.deleted_at = timezone.now()
            acionista.deleted_by = request.user
            acionista.is_active = False
            acionista.save(update_fields=['deleted_at', 'deleted_by', 'is_active', 'updated_at'])
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = AcionistaClienteSerializer(acionista, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
