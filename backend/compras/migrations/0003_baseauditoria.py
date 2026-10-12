# Manutencao 62 — auditoria BaseModel (created_by/updated_by/deleted_by/deleted_at)
# + ItemCompra passa a herdar BaseModel (RF-13).
import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('compras', '0002_categoria_compra_mercadoria'),
    ]

    operations = [
        migrations.AddField(
            model_name='compra',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='compra',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='compra',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='compra',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
        migrations.AddField(
            model_name='itemcompra',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=datetime.datetime(2026, 10, 12, 3, 43, 9, 824730, tzinfo=datetime.timezone.utc), verbose_name='criado em'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='itemcompra',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='criado por'),
        ),
        migrations.AddField(
            model_name='itemcompra',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='excluído em'),
        ),
        migrations.AddField(
            model_name='itemcompra',
            name='deleted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='excluído por'),
        ),
        migrations.AddField(
            model_name='itemcompra',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='ativo'),
        ),
        migrations.AddField(
            model_name='itemcompra',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='atualizado em'),
        ),
        migrations.AddField(
            model_name='itemcompra',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por'),
        ),
    ]
