from rest_framework import serializers

from .models import Cargo, Colaborador, FolhaPagamento, RegistroFerias


class CargoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = Cargo
        fields = ['id', 'nome', 'descricao', 'salario_base', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class ColaboradorSerializer(serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    cargo_nome   = serializers.CharField(source='cargo.nome', read_only=True)
    regime_label = serializers.CharField(source='get_regime_display', read_only=True)
    tem_acesso   = serializers.SerializerMethodField()
    usuario_email = serializers.CharField(source='usuario.email', read_only=True, default=None)

    class Meta:
        model = Colaborador
        fields = [
            'id', 'nome', 'cpf', 'email', 'cargo', 'cargo_nome',
            'data_admissao', 'data_demissao', 'salario_atual',
            'regime', 'regime_label', 'observacoes', 'is_active', 'created_at',
            'tem_acesso', 'usuario_email',
        ]
        read_only_fields = ['id', 'cargo_nome', 'regime_label', 'created_at', 'tem_acesso', 'usuario_email']

    def get_tem_acesso(self, obj):
        return obj.usuario_id is not None


class FolhaPagamentoSerializer(serializers.ModelSerializer):
    id               = serializers.IntegerField(source='pk', read_only=True)
    colaborador_nome = serializers.CharField(source='colaborador.nome', read_only=True)
    status_label     = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = FolhaPagamento
        fields = [
            'id', 'colaborador', 'colaborador_nome', 'mes_referencia',
            'salario_bruto', 'descontos', 'salario_liquido',
            'status', 'status_label', 'observacoes', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'colaborador_nome', 'salario_liquido', 'status_label', 'created_at']


class RegistroFeriasSerializer(serializers.ModelSerializer):
    id               = serializers.IntegerField(source='pk', read_only=True)
    colaborador_nome = serializers.CharField(source='colaborador.nome', read_only=True)
    status_label     = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = RegistroFerias
        fields = [
            'id', 'colaborador', 'colaborador_nome', 'data_inicio', 'data_fim',
            'dias', 'status', 'status_label', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'colaborador_nome', 'dias', 'status_label', 'created_at']
