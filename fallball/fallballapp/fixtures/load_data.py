import binascii
import os

from django.conf import settings

from fallballapp.meta_data import data
from fallballapp.utils import get_app_username


def load_data(apps, schema_editor):
    user_admin, created = apps.get_model('auth', 'User').objects.get_or_create(
        username='admin',
        password='pbkdf2_sha256$24000$ZVxkeukDOSaR$BkbfzKABp5MTWFALbWbggsunbYjTWYn8G/+tWMktZZg=',
        is_superuser=True,
        is_staff=True)

    apps.get_model('authtoken', 'Token').objects.get_or_create(
        pk=settings.ADMIN_AUTH_TOKEN,
        user=user_admin)

    user_app, created = apps.get_model('auth', 'User').objects.get_or_create(
        username='new_app',
        is_superuser=False,
        is_staff=False)

    apps.get_model('authtoken', 'Token').objects.get_or_create(
            user=user_app,
            pk=binascii.hexlify(os.urandom(20)).decode())

    app, created = apps.get_model('fallballapp', 'Application').objects.get_or_create(
        pk='new_app',
        owner=user_app)

    for reseller_template in data:
        username = get_app_username(app.id, reseller_template['name'])
        owner, created = apps.get_model('auth', 'User').objects.get_or_create(username=username)
        apps.get_model('authtoken', 'Token').objects.get_or_create(
            user=owner,
            pk=binascii.hexlify(os.urandom(20)).decode())
        params = dict.copy(reseller_template)
        params.pop('clients', None)

        reseller, created = apps.get_model('fallballapp', 'Reseller').objects.get_or_create(
            application=app,
            owner=owner,
            **params)

        if 'clients' in reseller_template:
            for client_template in reseller_template['clients']:
                params = dict.copy(client_template)
                params.pop('users', None)
                client = apps.get_model('fallballapp', 'Client').objects.create(
                    reseller=reseller,
                    **params)

                if 'users' in client_template:
                    for user_template in client_template['users']:
                        username = get_app_username(app.id, user_template['user_id'])
                        owner, created = apps.get_model('auth', 'User').objects.get_or_create(
                            username=username)
                        apps.get_model('authtoken', 'Token').objects.get_or_create(
                            user=owner,
                            pk=binascii.hexlify(os.urandom(20)).decode())
                        params = dict.copy(user_template)
                        params.pop('users', None)
                        apps.get_model('fallballapp', 'ClientUser').objects.create(
                            client=client,
                            owner=owner,
                            **params)
