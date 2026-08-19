from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import generics, permissions, status
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from common.permissions import IsAdmin

from .models import User
from .serializers import RegisterSerializer, UserAdminSerializer, UserSerializer


class UserViewSet(ModelViewSet):
    """Tela de Usuarios (IsAdmin) — cria/edita/lista/desativa qualquer User do sistema."""
    queryset = User.objects.all().select_related('colaborador').order_by('-date_joined')
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdmin]
    filter_backends = [SearchFilter]
    search_fields = ['email', 'nome_completo']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class AlterarSenhaView(APIView):
    """Usuario logado troca a propria senha."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        senha_atual = request.data.get('senha_atual', '')
        senha_nova = request.data.get('senha_nova', '')

        if not senha_atual or not senha_nova:
            return Response({'erro': 'Preencha todos os campos.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(senha_nova) < 6:
            return Response({'erro': 'A nova senha deve ter pelo menos 6 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.check_password(senha_atual):
            return Response({'erro': 'Senha atual incorreta.'}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(senha_nova)
        request.user.save()
        return Response({'mensagem': 'Senha alterada com sucesso.'})


class SolicitarAcessoView(APIView):
    """ADMIN envia email de primeiro acesso para um usuario."""
    permission_classes = [IsAdmin]

    def post(self, request):
        from .services import enviar_primeiro_acesso

        usuario_id = request.data.get('usuario_id')
        try:
            usuario = User.objects.get(pk=usuario_id, is_active=True)
        except User.DoesNotExist:
            return Response({'erro': 'Usuario nao encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            enviar_primeiro_acesso(usuario)
        except Exception as e:
            return Response({'erro': f'Erro ao enviar email: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'mensagem': f'Email de acesso enviado para {usuario.email}.'})


class DefinirSenhaView(APIView):
    """Valida token e define senha — sem autenticacao."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uid_b64 = request.data.get('uid', '')
        token = request.data.get('token', '')
        senha = request.data.get('senha', '')

        if not uid_b64 or not token or not senha:
            return Response({'erro': 'Dados incompletos.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(senha) < 6:
            return Response({'erro': 'A senha deve ter pelo menos 6 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(uid_b64))
            usuario = User.objects.get(pk=uid)
        except (ValueError, User.DoesNotExist):
            return Response({'erro': 'Link invalido.'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(usuario, token):
            return Response(
                {'erro': 'Link expirado ou invalido. Solicite um novo email de acesso.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario.set_password(senha)
        usuario.save()
        return Response({'mensagem': 'Senha definida com sucesso. Voce ja pode fazer login.'})
