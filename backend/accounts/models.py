from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from .managers import CustomUserManager


class PerfilUsuario(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    OPERACIONAL = 'OPERACIONAL', 'Operacional'
    MARKETING = 'MARKETING', 'Marketing'
    SUPERADMIN = 'SUPERADMIN', 'Superadmin'
    FINANCEIRO = 'FINANCEIRO', 'Financeiro'          # Manutencao 63 (RF-01)
    PROFISSIONAL = 'PROFISSIONAL', 'Profissional'    # Manutencao 63 (RF-01)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField('e-mail', unique=True)
    nome_completo = models.CharField('nome completo', max_length=255)
    telefone = models.CharField('telefone', max_length=20, blank=True)
    is_active = models.BooleanField('ativo', default=True)
    is_staff = models.BooleanField('membro da equipe', default=False)
    perfil = models.CharField(
        'perfil', max_length=12,
        choices=PerfilUsuario.choices, default=PerfilUsuario.OPERACIONAL,
    )
    date_joined = models.DateTimeField('data de cadastro', auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome_completo']

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    @property
    def tem_acesso_total(self):
        """
        Manutencao 60 -- unifica toda checagem de negocio de "e admin" num
        so lugar. is_staff continua controlando so o Django Admin
        (PermissionsMixin/createsuperuser), sem mudar de significado --
        aditivo/retrocompativel: is_staff=True sempre concede acesso
        total, independente do perfil (RN-01).
        """
        return self.is_staff or self.perfil in (PerfilUsuario.ADMIN, PerfilUsuario.SUPERADMIN)
