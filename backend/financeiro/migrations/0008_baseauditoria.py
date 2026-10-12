# Manutencao 62 — auditoria BaseModel (created_by/updated_by/deleted_by/deleted_at)
# + LivroCaixa.criado_por renomeado para created_by (RenameField preserva o
# dado — LivroCaixa NAO herda BaseModel, e' rename simples de FK, ver 2.5
# da Especificacao Hotfix).
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('financeiro', '0007_estornoreceita_item_venda_estornoreceita_receita'),
    ]

    operations = [
        migrations.RenameField(
            model_name='livrocaixa',
            old_name='criado_por',
            new_name='created_by',
        ),
        migrations.AddField(
            model_name='aporte',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='aporte',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='aporte',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='aporte',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='conciliacaoextrato',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='conciliacaoextrato',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='conciliacaoextrato',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='conciliacaoextrato',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='conta',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='conta',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='conta',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='conta',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='despesa',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='despesa',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='despesa',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='despesa',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='estornoreceita',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='estornoreceita',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='estornoreceita',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='estornoreceita',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='itemconciliacao',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='itemconciliacao',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='itemconciliacao',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='itemconciliacao',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='padraoseguroconciliacao',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='padraoseguroconciliacao',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='padraoseguroconciliacao',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='padraoseguroconciliacao',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='receita',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='receita',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='receita',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='receita',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
    ]
