from decimal import ROUND_HALF_UP, Decimal

from rest_framework import serializers

from common.serializers import AuditFieldsMixin

from .models import Aporte, Categoria, Conta, Despesa, EstornoReceita, LivroCaixa, Receita, TipoDesconto


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
        # Manutencao #90 (RN-07) — 'assinatura' SAI de read_only_fields:
        # passa a ser gravavel na CRIACAO (fluxo manual de Nova Receita
        # vinculando a uma assinatura ativa, RF-03/06). Antes disso so
        # assinaturas.services.gerar_cobrancas_mes gravava esse FK (via
        # Receita.objects.get_or_create, direto no ORM, nunca pelo
        # serializer) — esse fluxo continua intacto, nao passa por aqui.
        # Imutabilidade pos-criacao e garantida em validate(), nao aqui.
        read_only_fields = ['valor_liquido', 'created_at']
        # aceita 'AAAA-MM' (input type=month); campo auto-gerado mantido de
        # proposito: o UniqueConstraint condicional (assinatura, referencia_mes)
        # depende do tratamento que o DRF da ao campo gerado.
        extra_kwargs = {'referencia_mes': {'input_formats': ['%Y-%m', 'iso-8601']}}

    def validate(self, data):
        bruto = data.get('valor_bruto', getattr(self.instance, 'valor_bruto', Decimal('0')))
        desconto = data.get('desconto', getattr(self.instance, 'desconto', Decimal('0')))
        if desconto > bruto:
            raise serializers.ValidationError({'desconto': 'Desconto não pode ser maior que o valor bruto.'})

        # RN-07: assinatura imutavel apos criacao — so pode ser definida no
        # POST de criacao; PATCH/PUT que tenta mudar o vinculo e rejeitado.
        if self.instance and 'assinatura' in data:
            nova = data['assinatura']
            atual = self.instance.assinatura
            if (nova.pk if nova else None) != (atual.pk if atual else None):
                raise serializers.ValidationError(
                    {'assinatura': 'Não é possível alterar a assinatura vinculada após a criação.'}
                )

        assinatura = data.get('assinatura', getattr(self.instance, 'assinatura', None))
        cliente = data.get('cliente', getattr(self.instance, 'cliente', None))
        referencia_mes = data.get('referencia_mes', getattr(self.instance, 'referencia_mes', None))

        if assinatura:
            # RN-09 — assinatura informada precisa pertencer ao cliente informado.
            if cliente and assinatura.cliente_id != cliente.pk:
                raise serializers.ValidationError(
                    {'assinatura': 'A assinatura informada não pertence ao cliente selecionado.'}
                )
            # RN-08 — nao duplicar receita da mesma assinatura no mesmo mes
            # de referencia. Complementar (nao substitui) a UniqueConstraint
            # uniq_assinatura_referencia_mes ja existente no model.
            if referencia_mes:
                conflito_qs = Receita.objects.filter(
                    assinatura_id=assinatura.pk, referencia_mes=referencia_mes, is_active=True,
                ).exclude(status='CANCELADO')
                if self.instance:
                    conflito_qs = conflito_qs.exclude(pk=self.instance.pk)
                existente = conflito_qs.first()
                if existente:
                    raise serializers.ValidationError({
                        'assinatura': (
                            f'Já existe uma receita para esta assinatura no mês de referência '
                            f'informado (Receita #{existente.pk}, status {existente.get_status_display()}).'
                        )
                    })
        return data

    # Achado ao implementar a Manutencao #90: a UniqueConstraint de banco
    # 'uniq_assinatura_referencia_mes' (Receita.Meta.constraints, desde a
    # Manutencao #64) e INCONDICIONAL quanto a status/is_active — so
    # exige assinatura nao-nula, nunca exclui CANCELADO. O validate()
    # acima, seguindo RN-08 a risca, EXCLUI CANCELADO da checagem amigavel
    # (para permitir reabrir o mes depois de cancelar) — mas isso deixa um
    # buraco real: se a unica Receita existente para aquela
    # assinatura+mes estiver CANCELADO, validate() nao acha conflito e
    # deixa passar, e so então a constraint de banco (que nao sabe o que
    # e CANCELADO) rejeita com IntegrityError puro, que sem este guard
    # vazaria como 500. Mesmo precedente ja usado nesta fabrica
    # (produtos/views.py, pdv/services.py: "nunca deploy com erro
    # generico de integridade") — nunca alterar/migrar a constraint
    # aqui, so blindar o ponto de insercao.
    def create(self, validated_data):
        # transaction.atomic() aqui cria um SAVEPOINT (mesmo dentro do
        # atomic por-teste do TestCase) -- sem isso, capturar o
        # IntegrityError deixaria a transacao inteira "precisa de
        # rollback" para qualquer query seguinte (TransactionManagementError),
        # tanto em teste quanto em producao com ATOMIC_REQUESTS.
        from django.db import IntegrityError, transaction
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({
                'assinatura': (
                    'Já existe uma receita para esta assinatura no mês de referência '
                    'informado.'
                )
            })

    def update(self, instance, validated_data):
        from django.db import IntegrityError, transaction
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({
                'assinatura': (
                    'Já existe uma receita para esta assinatura no mês de referência '
                    'informado.'
                )
            })


class DespesaSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)
    # Manutencao 89 (RF-05): fornecedor_fk/subcategoria convivem com os
    # campos legados (fornecedor texto, categoria) — nunca os substituem.
    fornecedor_fk_nome = serializers.CharField(
        source='fornecedor_fk.nome_razao_social', read_only=True, default='', allow_null=True,
    )
    subcategoria_nome = serializers.CharField(
        source='subcategoria.nome', read_only=True, default='', allow_null=True,
    )

    class Meta:
        model = Despesa
        fields = [
            'id', 'tipo', 'descricao', 'fornecedor',
            'fornecedor_fk', 'fornecedor_fk_nome',
            'valor_bruto', 'desconto', 'tipo_desconto', 'percentual_desconto', 'valor_liquido',
            'conta', 'conta_nome',
            'categoria', 'categoria_nome', 'subcategoria', 'subcategoria_nome',
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
        # RF-03/RN-04 (Manutencao 89): subcategoria so e aceita se tiver
        # pai (e' de fato uma subcategoria) e, se categoria tambem vier no
        # payload, o pai da subcategoria tem que ser essa categoria.
        subcategoria = data.get(
            'subcategoria', getattr(self.instance, 'subcategoria', None) if self.instance else None,
        )
        if subcategoria is not None:
            if subcategoria.pai_id is None:
                raise serializers.ValidationError(
                    {'subcategoria': 'A categoria informada não é uma subcategoria (não possui categoria-pai).'}
                )
            categoria = data.get(
                'categoria', getattr(self.instance, 'categoria', None) if self.instance else None,
            )
            if categoria is not None and subcategoria.pai_id != categoria.id:
                raise serializers.ValidationError(
                    {'subcategoria': 'A subcategoria informada não pertence à categoria selecionada.'}
                )

        # RF-04/RN-03 (Manutencao 89): desconto em % resolvido em Decimal,
        # sobrescrevendo o `desconto` em R$ que vier no payload — a % manda.
        tipo_desconto = data.get(
            'tipo_desconto', getattr(self.instance, 'tipo_desconto', TipoDesconto.VALOR) if self.instance else TipoDesconto.VALOR,
        )
        bruto = data.get('valor_bruto', getattr(self.instance, 'valor_bruto', Decimal('0')))

        if tipo_desconto == TipoDesconto.PERCENTUAL:
            percentual = data.get(
                'percentual_desconto',
                getattr(self.instance, 'percentual_desconto', Decimal('0')) if self.instance else Decimal('0'),
            )
            if percentual is None:
                percentual = Decimal('0')
            if percentual < 0 or percentual > 100:
                raise serializers.ValidationError(
                    {'percentual_desconto': 'Percentual de desconto deve estar entre 0 e 100.'}
                )
            data['percentual_desconto'] = percentual
            data['desconto'] = (bruto * percentual / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP,
            )
        else:
            data['percentual_desconto'] = Decimal('0')

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
