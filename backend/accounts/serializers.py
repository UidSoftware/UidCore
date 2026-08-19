from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'nome_completo', 'telefone', 'is_active', 'is_staff', 'date_joined']
        read_only_fields = ['id', 'is_active', 'is_staff', 'date_joined']


class UserAdminSerializer(serializers.ModelSerializer):
    """Usada pela tela de Usuarios (IsAdmin) — cria/edita qualquer User do sistema."""
    id = serializers.IntegerField(source='pk', read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    colaborador_nome = serializers.CharField(source='colaborador.nome', read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'nome_completo', 'telefone', 'password',
            'is_active', 'is_staff', 'date_joined', 'colaborador_nome',
        ]
        read_only_fields = ['id', 'date_joined', 'colaborador_nome']

    def create(self, validated_data):
        senha = validated_data.pop('password', '')
        usuario = User(**validated_data)
        if senha:
            usuario.set_password(senha)
        else:
            usuario.set_unusable_password()
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        senha = validated_data.pop('password', '')
        usuario = super().update(instance, validated_data)
        if senha:
            usuario.set_password(senha)
            usuario.save(update_fields=['password'])
        return usuario


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'nome_completo', 'telefone', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password': 'As senhas não conferem.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(**validated_data)
