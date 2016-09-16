from datetime import datetime

from django.contrib.auth.models import User

from fallballapp.models import Reseller, Client, ClientUser
from fallballapp.utils import get_app_username

data = [
    {
        'name': 'reseller_a',
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
                        'email': 'johnson@sunnyflowers.tld',
                        'usage': 3,
                        'admin': False,
                        'password': 'password',
                        'limit': 5
                    },
                    {
                        'email': 'brown@sunnyflowers.tld',
                        'usage': 2,
                        'admin': False,
                        'password': 'password',
                        'limit': 6
                    },
                    {
                        'email': 'williams@sunnyflowers.tld',
                        'usage': 1,
                        'admin': True,
                        'password': 'password',
                        'limit': 4
                    }
                ]
            }
        ]
    },
    {
        'name': 'reseller_b',
        'limit': 350
    },
    {
        'name': 'reseller_c',
        'limit': 400
    }
]


def load_app_data(app_instance):
    for reseller_template in data:
        username = get_app_username(app_instance.id, reseller_template['name'])
        owner = User.objects.create_user(username=username)
        params = dict.copy(reseller_template)
        params.pop('clients', None)
        reseller = Reseller.objects.create(application=app_instance, owner=owner,
                                           **params)

        if 'clients' in reseller_template:
            for client_template in reseller_template['clients']:
                params = dict.copy(client_template)
                params.pop('users', None)
                client = Client.objects.create(reseller=reseller, **params)

                if 'users' in client_template:
                    for user_template in client_template['users']:
                        username = get_app_username(app_instance.id, user_template['email'])
                        owner = User.objects.create_user(username=username,
                                                         password=user_template['password'])
                        params = dict.copy(user_template)
                        params.pop('users', None)
                        ClientUser.objects.create(client=client, user=owner, **params)
