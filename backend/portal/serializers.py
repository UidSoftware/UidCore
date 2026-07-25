from rest_framework import serializers

from .models import AcessoPortalCliente


class AcessoPortalClienteSerializer(serializers.ModelSerializer):
    id            = serializers.IntegerField(source='pk', read_only=True)
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True)
    cliente_nome  = serializers.CharField(source='cliente.nome_razao_social', read_only=True)

    class Meta:
        model = AcessoPortalCliente
        fields = [
            'id', 'usuario', 'usuario_email', 'cliente', 'cliente_nome',
            'ativo', 'ultimo_acesso', 'criado_em',
        ]
        read_only_fields = ['id', 'usuario_email', 'cliente_nome', 'ultimo_acesso', 'criado_em']
