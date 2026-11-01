from decimal import Decimal

from rest_framework import serializers

from common.serializers import AuditFieldsMixin

from .models import Aporte, Categoria, Conta, Despesa, EstornoReceita, LivroCaixa, Receita


class CategoriaSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    # RF-03 (Manutencao 88): pai_nome/subcategorias_count sao leitura —
    # frontend usa subcategorias_count para avisar antes de excluir
    # categoria-pai (RN-06 bloqueia no backend, isso e so UX).
    pai_nome = serializers.CharField(source='pai.nome', read_only=True, default='', allow_null=True)
    subcategorias_count = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = [
            'id', 'nome', 'tipo', 'pai', 'pai_nome', 'subcategorias_count',
            'is_active', 'created_at', 'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = ['created_at']

    def get_subcategorias_count(self, obj):
        return obj.subcategorias.filter(is_active=True).count()

    def validate(self, attrs):
        # RF-02/RN-01/RN-02/RN-03: pai so pode ser resolvido olhando o
        # estado final (tipo/pai podem nao vir os dois no PATCH parcial).
        pai = attrs.get('pai', getattr(self.instance, 'pai', None) if self.instance else None)
        tipo = attrs.get('tipo', getattr(self.instance, 'tipo', None) if self.instance else None)

        if pai is None:
            return attrs

        # RN-02: categoria nao pode ser pai de si mesma.
        if self.instance is not None and pai.pk == self.instance.pk:
            raise serializers.ValidationError({'pai': 'Uma categoria não pode ser pai de si mesma.'})

        # RF-02/RN-03: subcategoria deve ser do mesmo tipo do pai.
        if tipo and pai.tipo != tipo:
            raise serializers.ValidationError(
                {'pai': 'A subcategoria deve ser do mesmo tipo da categoria-pai.'}
            )

        # RF-02/RN-03: pai nao pode ja ser subcategoria (nesting > 1 nivel).
        if pai.pai_id is not None:
            raise serializers.ValidationError(
                {'pai': 'Uma subcategoria não pode ter subcategorias (máximo 1 nível).'}
            )

        # RN-01: categoria com subcategoria ativa nao pode, ela mesma,
        # receber um pai (nao inverte hierarquia).
        if self.instance is not None and self.instance.subcategorias.filter(is_active=True).exists():
            raise serializers.ValidationError(
                {'pai': 'Esta categoria já possui subcategorias e não pode receber um pai.'}
            )

        return attrs


class ContaSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    saldo_atual = serializers.SerializerMethodField()

    class Meta:
        model = Conta
        fields = [
            'id', 'nome', 'tipo', 'banco', 'agencia', 'numero',
            'saldo_inicial', 'saldo_atual', 'is_active', 'created_at',
            'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = ['created_at']

    def get_saldo_atual(self, obj):
        from .services import saldo_real
        return saldo_real(obj)


class AporteSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)

    class Meta:
        model = Aporte
        fields = [
            'id', 'tipo', 'descricao', 'valor', 'conta', 'conta_nome',
            'data', 'responsavel', 'observacoes', 'is_active', 'created_at',
            'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = ['created_at']


class ReceitaSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    cliente_nome = serializers.CharField(source='cliente.nome_razao_social', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)
    class Meta:
        model = Receita
        fields = [
            'id', 'tipo', 'descricao',
            'cliente', 'cliente_nome',
            'categoria', 'categoria_nome',
            'valor_bruto', 'desconto', 'valor_liquido',
            'conta', 'conta_nome',
            'vencimento', 'recebimento', 'status',
            'referencia_mes', 'assinatura', 'observacoes', 'is_active', 'created_at',
            'created_by_nome', 'updated_by_nome',
        ]
        # 'assinatura' e read_only aqui (Manutencao #64 [NUCLEO 3/5]) --
        # o vinculo so e criado por assinaturas.services.gerar_cobrancas_mes
        # (via Receita.objects.get_or_create, direto no ORM, nao pelo
        # serializer). Exposto so para leitura (ex: aba Assinaturas na
        # ficha do Cliente, RF-11).
        read_only_fields = ['valor_liquido', 'created_at', 'assinatura']
        # aceita 'AAAA-MM' (input type=month); campo auto-gerado mantido de
        # proposito: o UniqueConstraint condicional (assinatura, referencia_mes)
        # depende do tratamento que o DRF da ao campo gerado.
        extra_kwargs = {'referencia_mes': {'input_formats': ['%Y-%m', 'iso-8601']}}

    def validate(self, data):
        bruto = data.get('valor_bruto', getattr(self.instance, 'valor_bruto', Decimal('0')))
        desconto = data.get('desconto', getattr(self.instance, 'desconto', Decimal('0')))
        if desconto > bruto:
            raise serializers.ValidationError({'desconto': 'Desconto não pode ser maior que o valor bruto.'})
        return data


class DespesaSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)
    class Meta:
        model = Despesa
        fields = [
            'id', 'tipo', 'descricao', 'fornecedor',
            'valor_bruto', 'desconto', 'valor_liquido',
            'conta', 'conta_nome',
            'categoria', 'categoria_nome',
            'vencimento', 'pagamento', 'forma_pagamento', 'status',
            'referencia_mes', 'comprovante', 'observacoes',
            'recorrente', 'frequencia', 'quantidade',
            'estornado', 'data_estorno', 'motivo_estorno',
            'is_active', 'created_at', 'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = ['valor_liquido', 'estornado', 'data_estorno', 'motivo_estorno', 'created_at']
        # aceita 'AAAA-MM' (input type=month); campo auto-gerado mantido de
        # proposito: o UniqueConstraint condicional (assinatura, referencia_mes)
        # depende do tratamento que o DRF da ao campo gerado.
        extra_kwargs = {'referencia_mes': {'input_formats': ['%Y-%m', 'iso-8601']}}

    def validate(self, data):
        bruto = data.get('valor_bruto', getattr(self.instance, 'valor_bruto', Decimal('0')))
        desconto = data.get('desconto', getattr(self.instance, 'desconto', Decimal('0')))
        if desconto > bruto:
            raise serializers.ValidationError({'desconto': 'Desconto não pode ser maior que o valor bruto.'})
        return data


class LivroCaixaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)
    tipo_label = serializers.CharField(source='get_tipo_display', read_only=True)
    origem_label = serializers.CharField(source='get_origem_display', read_only=True)

    class Meta:
        model = LivroCaixa
        fields = [
            'id', 'conta', 'conta_nome',
            'tipo', 'tipo_label', 'origem', 'origem_label', 'origem_id',
            'descricao', 'valor', 'data',
            'saldo_anterior', 'saldo_atual',
            'criado_em', 'estornado', 'estorno_de',
        ]
        read_only_fields = [
            'criado_em', 'saldo_anterior', 'saldo_atual', 'estornado', 'estorno_de',
        ]


class EstornoReceitaSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = EstornoReceita
        fields = [
            'id', 'receita', 'valor', 'motivo', 'data_estorno', 'item_venda', 'created_at',
            'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = ['id', 'created_at']


# --- Conciliacao Bancaria ---

from .models import ConciliacaoExtrato, ItemConciliacao, PadraoSeguroConciliacao


class ConciliacaoExtratoSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    conta_nome   = serializers.CharField(source='conta.nome', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ConciliacaoExtrato
        fields = [
            'id', 'conta', 'conta_nome', 'arquivo_nome', 'periodo',
            'processado_em', 'status', 'status_label',
            'total_banco', 'total_sistema', 'divergencias',
            'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = [
            'id', 'conta_nome', 'processado_em', 'status', 'status_label',
            'total_banco', 'total_sistema', 'divergencias',
        ]


class ItemConciliacaoSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    tipo_label   = serializers.CharField(source='get_tipo_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ItemConciliacao
        fields = [
            'id', 'conciliacao', 'data_banco', 'descricao_banco',
            'valor', 'tipo', 'tipo_label', 'status', 'status_label',
            'lancamento_lc', 'confirmado', 'is_active', 'created_at',
            'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = ['created_at']


class PadraoSeguroConciliacaoSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id             = serializers.IntegerField(source='pk', read_only=True)
    tipo_label     = serializers.CharField(source='get_tipo_display', read_only=True)
    natureza_label = serializers.CharField(source='get_natureza_display', read_only=True)

    class Meta:
        model = PadraoSeguroConciliacao
        fields = [
            'id', 'descricao_padrao', 'tipo', 'tipo_label',
            'natureza', 'natureza_label', 'is_active', 'created_at',
            'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = ['created_at']
