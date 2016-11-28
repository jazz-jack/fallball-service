from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from fallballapp.models import Application, Reseller, ClientUser
from fallballapp.meta_data import load_app_data


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        if not instance.is_superuser:
            Token.objects.create(user=instance)


@receiver(post_save, sender=Application)
def load_fixtures(instance=None, created=False, **kwargs):
    if not created:
        return
    load_app_data(instance)


@receiver(post_delete, sender=Reseller)
def delete_reseller_user(instance=None, **kwargs):
    instance.owner.delete()


@receiver(post_delete, sender=Application)
def delete_app_user(instance=None, **kwargs):
    instance.owner.delete()


@receiver(post_delete, sender=ClientUser)
def delete_client_user(instance=None, **kwargs):
    instance.owner.delete()
