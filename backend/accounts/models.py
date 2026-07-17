from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from .managers import CustomUserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField('e-mail', unique=True)
    nome_completo = models.CharField('nome completo', max_length=255)
    telefone = models.CharField('telefone', max_length=20, blank=True)
    is_active = models.BooleanField('ativo', default=True)
    is_staff = models.BooleanField('membro da equipe', default=False)
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
