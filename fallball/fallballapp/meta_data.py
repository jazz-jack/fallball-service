from datetime import datetime
import uuid

from django.contrib.auth import get_user_model

from fallballapp.models import Reseller, Client, ClientUser
from fallballapp.utils import get_app_username

data = [
    {
        'name': 'reseller_a',
        'rid': '32f57666-6e78-4080-b1c0-43111d2b5af8',
        'limit': 300,
        'clients': [
            {
                'name': 'MadRobots',
                'creation_date': datetime.now(),
                'limit': 40
            },
            {
                'name': 'MyDevs',
                'creation_date': datetime.now(),
                'limit': 30
            },
            {
                'name': 'SunnyFlowers',
                'creation_date': datetime.now(),
                'limit': 50,
                'users': [
                    {
                        'user_id': uuid.uuid4(),
                        'email': 'johnson@sunnyflowers.tld',
                        'usage': 3,
                        'admin': False,
                        'limit': 5
                    },
                    {
                        'user_id': uuid.uuid4(),
                        'email': 'brown@sunnyflowers.tld',
                        'usage': 2,
                        'admin': False,
                        'limit': 6
                    },
                    {
                        'user_id': uuid.uuid4(),
                        'email': 'williams@sunnyflowers.tld',
                        'usage': 1,
                        'admin': True,
                        'limit': 4
                    }
                ]
            }
        ]
    },
    {
        'name': 'reseller_b',
        'rid': 'f0e75b19-e668-48ef-92c5-af309faf3735',
        'limit': 350
    },
    {
        'name': 'reseller_c',
        'rid': '40a230cd-e2cb-4176-b384-05a185ed1028',
        'limit': 400
    }
]


def load_app_data(app_instance):
    for reseller_template in data:
        username = get_app_username(app_instance.id, reseller_template['name'])
        owner = get_user_model().objects.create_user(username=username)
        params = dict.copy(reseller_template)
        params.pop('clients', None)

        reseller = Reseller.objects.create(application=app_instance, owner=owner, **params)

        if 'clients' in reseller_template:
            for client_template in reseller_template['clients']:
                params = dict.copy(client_template)
                params.pop('users', None)
                client = Client.objects.create(reseller=reseller, **params)

                if 'users' in client_template:
                    for user_template in client_template['users']:
                        username = get_app_username(app_instance.id, user_template['user_id'])
                        owner = get_user_model().objects.create_user(username=username)
                        params = dict.copy(user_template)
                        params.pop('users', None)
                        ClientUser.objects.create(client=client, owner=owner, **params)
