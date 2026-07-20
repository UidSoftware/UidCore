from django.db import models
from common.models import PessoaBase


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
