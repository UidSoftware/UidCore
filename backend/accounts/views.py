from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from common.permissions import IsAdmin

from .models import PerfilUsuario, User
from .serializers import RegisterSerializer, UserAdminSerializer, UserSerializer


class UserViewSet(ModelViewSet):
    """Tela de Usuarios (IsAdmin) — cria/edita/lista/desativa qualquer User do sistema."""
    queryset = User.objects.all().select_related('colaborador').order_by('-date_joined')
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdmin]
    filter_backends = [SearchFilter]
    search_fields = ['email', 'nome_completo']

    def _bloquear_edicao_superadmin(self, instance):
        """
        RF-07/RN-03 (Manutencao 60): so um SUPERADMIN pode editar ou
        desativar outra conta SUPERADMIN. Um SUPERADMIN editando outro
        SUPERADMIN (ou a si mesmo) passa normalmente.
        """
        if instance.perfil == PerfilUsuario.SUPERADMIN and self.request.user.perfil != PerfilUsuario.SUPERADMIN:
            raise PermissionDenied('Somente um usuário Superadmin pode editar ou desativar outra conta Superadmin.')

    def perform_update(self, serializer):
        self._bloquear_edicao_superadmin(serializer.instance)
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        # Manutencao 62 (RF-07): accounts.User NAO herda common.models.
        # BaseModel (RN-07 — AbstractBaseUser, sem deleted_at/deleted_by) —
        # por isso NAO usa common.mixins.AuditMixin aqui (seu
        # perform_destroy grava deleted_at/deleted_by, campos inexistentes
        # em User, o que levantaria ValueError no instance.save(update_
        # fields=[...])). Mantem o soft delete simples (is_active=False)
        # que ja existia, preservando a checagem _bloquear_edicao_
        # superadmin antes de qualquer persistencia. destroy() generico do
        # ModelViewSet (DRF) ja chama self.perform_destroy(instance)
        # internamente, dispensando o override proprio de destroy().
        self._bloquear_edicao_superadmin(instance)
        instance.is_active = False
        instance.save(update_fields=['is_active'])


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


class FotoPerfilView(APIView):
    """
    Manutencao #72 (RF-02/RF-03) — usuario logado troca ou remove a
    propria foto de perfil. Opera SEMPRE sobre request.user (RN-01):
    nao recebe id de usuario na URL nem no body — ninguem altera foto de
    outra conta por aqui.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from django.core.exceptions import ValidationError

        from common.media import processar_foto

        arquivo = request.FILES.get('foto')
        if not arquivo:
            return Response({'erro': 'Envie o arquivo no campo "foto".'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            conteudo = processar_foto(arquivo)
        except ValidationError as e:
            mensagem = e.messages[0] if hasattr(e, 'messages') and e.messages else str(e)
            return Response({'erro': mensagem}, status=status.HTTP_400_BAD_REQUEST)

        usuario = request.user
        # RN-06: so apaga o arquivo antigo DEPOIS do novo ser salvo com
        # sucesso. Guardar so o nome (string) do arquivo antigo -- nunca a
        # referencia ao FieldFile em si: `usuario.foto` e `foto_antiga`
        # seriam o MESMO objeto (o descriptor do FileField cacheia a
        # instancia), entao `usuario.foto.save(...)` abaixo mutaria
        # `foto_antiga.name` tambem antes do delete, apagando o arquivo
        # NOVO que acabou de ser salvo em vez do antigo.
        nome_arquivo_antigo = usuario.foto.name if usuario.foto else None
        storage_antigo = usuario.foto.storage
        usuario.foto.save(conteudo.name, conteudo, save=True)
        if nome_arquivo_antigo:
            storage_antigo.delete(nome_arquivo_antigo)

        return Response({'foto_url': UserSerializer(usuario, context={'request': request}).data['foto_url']})

    def delete(self, request):
        usuario = request.user
        if usuario.foto:
            usuario.foto.delete(save=False)
            usuario.foto = None
            usuario.save(update_fields=['foto'])
        return Response({'foto_url': None})


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
