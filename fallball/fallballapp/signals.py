import json

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from fallballapp.models import Application, Reseller, Client, ClientUser
from fallballapp.utils import get_app_username


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        if not instance.is_superuser:
            Token.objects.create(user=instance)


@receiver(post_save, sender=Application)
def load_fixtures(instance=None, created=False, **kwargs):
    if not created:
        return
    
    with open(settings.APP_DATA) as data_file:
        data = json.load(data_file)
        for reseller_template in data:
            username = get_app_username(instance.id, reseller_template['name'])
            owner = User.objects.create(username=username)
            params = dict.copy(reseller_template)
            params.pop('clients', None)
            reseller = Reseller.objects.create(application=instance, owner=owner,
                                               **params)

            if 'clients' in reseller_template:
                for client_template in reseller_template['clients']:
                    params = dict.copy(client_template)
                    params.pop('users', None)
                    client = Client.objects.create(reseller=reseller, **params)

                    if 'users' in client_template:
                        for user_template in client_template['users']:
                            username = get_app_username(instance.id, user_template['email'])
                            owner = User.objects.create(username=username)
                            params = dict.copy(user_template)
                            params.pop('users', None)
                            ClientUser.objects.create(client=client, user=owner, **params)
