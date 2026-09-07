from django.db import migrations


def seed_superadmin(apps, schema_editor):
    """
    Manutencao 60 (RF-13/RN-06): promove contas legadas is_staff=True AND
    is_superuser=True para perfil=SUPERADMIN. Em seguida, se existir,
    forca a conta editoresdesucessos@gmail.com para perfil=ADMIN e
    is_staff=False -- usa .first() (nunca .get()) e so age dentro do if,
    para nao quebrar `migrate` em bases onde essa conta nao existe
    (ambiente de teste do Sentinel, CI, dev local). A ordem importa: se a
    etapa 2 rodasse antes da 1 e essa conta fosse is_staff=True AND
    is_superuser=True, a etapa 1 a promoveria de volta para SUPERADMIN.
    """
    User = apps.get_model('accounts', 'User')

    User.objects.filter(is_staff=True, is_superuser=True).update(perfil='SUPERADMIN')

    conta_especifica = User.objects.filter(email__iexact='editoresdesucessos@gmail.com').first()
    if conta_especifica:
        conta_especifica.perfil = 'ADMIN'
        conta_especifica.is_staff = False
        conta_especifica.save(update_fields=['perfil', 'is_staff'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_alter_user_perfil'),
    ]
    operations = [
        migrations.RunPython(seed_superadmin, noop),
    ]
