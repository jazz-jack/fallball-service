import json

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from fallballapp.models import Application, Reseller, Client, ClientUser
from fallballapp.utils import prepare_dict_for_model


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)

@receiver(post_save, sender=Application)
def load_fixtures(instance=None, created=False, **kwargs):
    if created:
        with open(settings.DBDUMP_FILE) as data_file:
            data = json.load(data_file)
            import ipdb; ipdb.set_trace()
            for item in data:
                item = prepare_dict_for_model(item)
                if item['model'] == 'fallballapp.reseller':
                    Reseller.objects.create(pk=item['pk'], application_id=instance.id,
                                            **item['fields'])

                elif item['model'] == 'fallballapp.client':
                    Client.objects.create(pk=item['pk'], **item['fields'])

                elif item['model'] == 'fallballapp.clientuser':
                    ClientUser.objects.create(pk=item['pk'], **item['fields'])
