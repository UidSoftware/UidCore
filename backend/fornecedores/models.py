from django.db import models, transaction
from common.models import BaseModel, PessoaBase


class CategoriaFornecedor(models.TextChoices):
    MATERIA_PRIMA = 'MATERIA_PRIMA', 'Matéria Prima'
    SERVICOS = 'SERVICOS', 'Serviços'
    TECNOLOGIA = 'TECNOLOGIA', 'Tecnologia'
    LOGISTICA = 'LOGISTICA', 'Logística'
    MANUTENCAO = 'MANUTENCAO', 'Manutenção'
    ESCRITORIO = 'ESCRITORIO', 'Material de Escritório'
    MARKETING = 'MARKETING', 'Marketing'
    OUTRO = 'OUTRO', 'Outro'


class Fornecedor(PessoaBase):
    categoria = models.CharField(
        'categoria', max_length=20,
        choices=CategoriaFornecedor.choices, default=CategoriaFornecedor.OUTRO,
    )
    contato_nome = models.CharField('nome do contato', max_length=150, blank=True)
    contato_telefone = models.CharField('telefone do contato', max_length=20, blank=True)
    website = models.URLField('website', blank=True)
    inscricao_estadual = models.CharField('inscrição estadual', max_length=20, blank=True)

    class Meta:
        db_table = 'fornecedores_fornecedor'
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['-created_at']

    def __str__(self):
        return self.nome_razao_social


class AcionistaFornecedor(BaseModel):
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE, related_name='acionistas')
    nome = models.CharField('nome', max_length=150)
    email = models.EmailField('e-mail', blank=True)
    cpf = models.CharField('CPF', max_length=11, blank=True, default='')
    telefone = models.CharField('telefone', max_length=20, blank=True)
    whatsapp = models.CharField('whatsapp', max_length=20, blank=True)
    principal = models.BooleanField('principal', default=False)

    class Meta:
        db_table = 'fornecedores_acionista'
        ordering = ['-principal', 'nome']
        verbose_name = 'Acionista'
        verbose_name_plural = 'Acionistas'

    def save(self, *args, **kwargs):
        if self.principal:
            with transaction.atomic():
                AcionistaFornecedor.objects.filter(
                    fornecedor=self.fornecedor, principal=True
                ).exclude(pk=self.pk).update(principal=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nome} ({self.fornecedor})'
