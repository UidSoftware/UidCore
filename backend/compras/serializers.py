from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from produtos.services import fator_para_base

from .models import Compra, ItemCompra


class ItemCompraSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    produto_nome = serializers.CharField(source='produto.nome', read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = ItemCompra
        fields = [
            'id', 'produto', 'produto_nome',
            'quantidade', 'unidade', 'valor_unitario_custo', 'subtotal',
        ]

    def validate(self, data):
        # RN-02: quantidade e valor_unitario_custo > 0
        if data['quantidade'] <= 0:
            raise serializers.ValidationError({'quantidade': 'Deve ser maior que zero.'})
        if data['valor_unitario_custo'] <= 0:
            raise serializers.ValidationError({'valor_unitario_custo': 'Deve ser maior que zero.'})
        # RN-01: sem fallback 1:1 silencioso — só valida aqui, o fator em
        # si é resolvido de novo (e reaproveitado) dentro de
        # MovimentoEstoque.save() no momento de criar o item de verdade.
        try:
            fator_para_base(data['produto'], data['unidade'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({
                'unidade': exc.messages if hasattr(exc, 'messages') else [str(exc)],
            })
        return data


class CompraSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    itens = ItemCompraSerializer(many=True)
    fornecedor_nome = serializers.CharField(source='fornecedor.nome_razao_social', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)

    class Meta:
        model = Compra
        fields = [
            'id', 'fornecedor', 'fornecedor_nome', 'conta', 'conta_nome',
            'numero_nota_fiscal', 'data_emissao', 'forma_pagamento', 'status',
            'valor_total', 'observacoes', 'itens', 'despesa',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['valor_total', 'despesa', 'is_active', 'created_at', 'updated_at']

    def validate_itens(self, value):
        if not value:
            raise serializers.ValidationError('A compra precisa ter pelo menos 1 item.')  # RN-02
        return value

    def create(self, validated_data):
        itens_data = validated_data.pop('itens')
        # RF-06.1: valor_total calculado no create() a partir da soma dos
        # itens do payload — nunca aceito diretamente (read_only acima).
        valor_total = sum(
            (item['quantidade'] * item['valor_unitario_custo'] for item in itens_data),
            Decimal('0.00'),
        )
        # RF-06.2: cria a Compra já com valor_total correto — dispara o
        # signal que gera a Despesa (RF-07) com o valor certo já na
        # primeira escrita.
        compra = Compra.objects.create(valor_total=valor_total, **validated_data)
        # RF-06.3: cria cada item em loop (dispara RF-04/RF-05 por item).
        for item in itens_data:
            ItemCompra.objects.create(compra=compra, **item)
        return compra


class CompraStatusUpdateSerializer(serializers.ModelSerializer):
    """RF-08: PATCH só aceita status (PENDENTE->PAGO, RN-06) e observacoes.
    fornecedor/conta/itens/valor_total nem entram nos fields — qualquer
    tentativa de envia-los no payload é simplesmente ignorada pelo DRF."""

    class Meta:
        model = Compra
        fields = ['status', 'observacoes']

    def validate_status(self, value):
        if self.instance.status != 'PENDENTE' or value != 'PAGO':
            raise serializers.ValidationError(
                'Única transição permitida via PATCH é PENDENTE -> PAGO.',
            )
        return value
