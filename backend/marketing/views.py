from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from clientes.models import Cliente
from common.permissions import IsAdmin, IsMarketing
from vendas.models import Pedido

from .models import Campanha, Lead, StatusLead
from .serializers import CampanhaSerializer, LeadSerializer


class CampanhaViewSet(viewsets.ModelViewSet):
    serializer_class = CampanhaSerializer
    permission_classes = [IsAdmin | IsMarketing]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'canal']
    search_fields = ['nome']

    def get_queryset(self):
        return Campanha.objects.filter(is_active=True)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='roi')
    def roi(self, request, pk=None):
        campanha = self.get_object()
        leads_qs = Lead.objects.filter(campanha=campanha, is_active=True)
        leads_total = leads_qs.count()
        leads_convertidos = leads_qs.filter(status=StatusLead.CONVERTIDO).count()

        clientes_ids = leads_qs.filter(
            status=StatusLead.CONVERTIDO, cliente_convertido__isnull=False,
        ).values_list('cliente_convertido_id', flat=True)

        receita_fechada = Pedido.objects.filter(
            cliente_id__in=clientes_ids,
            is_active=True,
            created_at__gte=campanha.data_inicio,
        ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0')

        orcamento = campanha.orcamento
        cac = (orcamento / leads_convertidos) if leads_convertidos > 0 else None
        roi = (
            ((receita_fechada - orcamento) / orcamento) * 100
            if orcamento > 0 else None
        )

        # RN01: campo monetario/decimal nunca vira float no JSON -- o encoder
        # padrao do DRF converte Decimal solto em float, perdendo precisao.
        # Fix Manutencao #54 (pos-Sentinel): serializar como string.
        return Response({
            'campanha_id': campanha.pk,
            'leads_total': leads_total,
            'leads_convertidos': leads_convertidos,
            'orcamento': str(orcamento),
            'receita_fechada': str(receita_fechada),
            'cac': str(cac) if cac is not None else None,
            'roi': str(roi) if roi is not None else None,
        })


class LeadViewSet(viewsets.ModelViewSet):
    serializer_class = LeadSerializer
    permission_classes = [IsAdmin | IsMarketing]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'campanha']
    search_fields = ['nome', 'email', 'telefone']

    def get_queryset(self):
        # RN07 — lead antigo continua visivel mesmo se a campanha for
        # arquivada depois (queryset nao filtra por campanha.is_active).
        return Lead.objects.filter(is_active=True)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='converter')
    def converter(self, request, pk=None):
        lead = self.get_object()
        if lead.status == StatusLead.CONVERTIDO:
            return Response({'detail': 'Lead já convertido.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            cliente = None
            if lead.email:
                cliente = Cliente.objects.filter(email=lead.email, is_active=True).first()
            if cliente is None:
                cliente = Cliente.objects.create(
                    tipo_pessoa='PF',
                    nome_razao_social=lead.nome,
                    email=lead.email,
                    telefone=lead.telefone,
                    origem=lead.campanha.nome if lead.campanha else 'Sem campanha',
                )
            lead.status = StatusLead.CONVERTIDO
            lead.cliente_convertido = cliente
            lead.save(update_fields=['status', 'cliente_convertido', 'updated_at'])

        return Response(LeadSerializer(lead).data, status=status.HTTP_200_OK)
