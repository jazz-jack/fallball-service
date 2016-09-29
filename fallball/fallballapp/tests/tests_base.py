import json
import random

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from fallballapp.models import Application, Reseller, Client, ClientUser


def _get_client(user_id):
    """
    Returns request object with admin token
    """
    client = APIClient()
    token = Token.objects.filter(user_id=user_id).first()
    if not token:
        token = Token.objects.create(user_id=user_id)
    client.credentials(HTTP_AUTHORIZATION='Token {token}'.format(token=token.key))
    return client


class BaseTestCase(TestCase):
    """
    Test basic operations: model objects create/delete
    """
    def setUp(self):
        admin = User.objects.filter(username='admin').first()
        if not admin:
            admin = User.objects.create_superuser('admin', 'admin@fallball.io', '1q2w3e')
        client_request = _get_client(admin.id)

        # create_application
        client_request.post('/v1/applications/',
                            json.dumps({'id': 'tricky_chicken'}),
                            content_type='application/json')

    def test_objects_creation(self):
        self.assertTrue(Application.objects.filter(id='tricky_chicken'))
        self.assertTrue(Reseller.objects.filter(name='reseller_a'))
        self.assertTrue(Reseller.objects.filter(name='reseller_b'))
        self.assertTrue(Client.objects.filter(name='SunnyFlowers'))
        self.assertTrue(ClientUser.objects.filter(email='williams@sunnyflowers.tld'))

    def test_creation_under_reseller(self):
        reseller = Reseller.objects.all().first()
        client_request = _get_client(reseller.owner)
        client_request.post('/v1/resellers/{}/clients/'.format(reseller.name),
                            json.dumps({'name': 'new_client', 'storage': {'limit': 200}}),
                            content_type='application/json')

        client_request.post('/v1/resellers/{}/clients/new_client/users/'.format(reseller.name),
                            json.dumps({'email': 'newuser@newclient.tld',
                                        'storage': {'limit': 30},
                                        'password': 'password'}),
                            content_type='application/json')

        self.assertTrue(Client.objects.filter(name='new_client'))
        self.assertTrue(ClientUser.objects.filter(email='newuser@newclient.tld'))

    def test_creation_under_app(self):
        app = Application.objects.all().first()
        client_request = _get_client(app.owner.id)

        reseller = Reseller.objects.filter(application=app).first()

        client_request.post('/v1/resellers/{}/clients/'.format(reseller.name),
                            json.dumps({'name': 'new_client', 'storage': {'limit': 200}}),
                            content_type='application/json')

        client_request.post('/v1/resellers/{}/clients/new_client/users/'.format(reseller.name),
                            json.dumps({'email': 'newuser@newclient.tld',
                                        'storage': {'limit': 30},
                                        'password': 'password'}),
                            content_type='application/json')

        self.assertTrue(Client.objects.filter(name='new_client'))
        self.assertTrue(ClientUser.objects.filter(email='newuser@newclient.tld'))

    def test_deleting_by_app(self):
        app = Application.objects.all().first()
        client_request = _get_client(app.owner.id)

        client = Client.objects.filter().first()
        reseller_name = client.reseller.name

        client_request.delete('/v1/resellers/{}/clients/{}/'.format(reseller_name,
                                                                    client.name),
                              content_type='application/json')
        self.assertFalse(Client.objects.filter(name=client.name))

        client_request.delete('/v1/resellers/{}/'.format(reseller_name),
                              content_type='application/json')
        self.assertFalse(Reseller.objects.filter(name=reseller_name))

    def test_deleting_by_reseller(self):
        reseller = Reseller.objects.all().first()
        client_request = _get_client(reseller.owner)

        client_user = ClientUser.objects.filter().first()
        client_name = client_user.client.name

        client_request.delete('/v1/resellers/{}/clients/{}/users/{}/'.format(reseller.name,
                                                                             client_name,
                                                                             client_user.email),
                              content_type='application/json')
        self.assertFalse(ClientUser.objects.filter(email=client_user.email))

        client_request.delete('/v1/resellers/{}/clients/{}/'.format(reseller.name,
                                                                    client_name),
                              content_type='application/json')
        self.assertFalse(Client.objects.filter(name=client_name))

    def test_duplicated_users(self):
        app = Application.objects.all().first()
        client_request = _get_client(app.owner.id)

        client_user = ClientUser.objects.filter().first()
        email = client_user.email
        client_name = client_user.client.name
        reseller_name = client_user.client.reseller.name

        request = client_request.post('/v1/resellers/{}/clients/{}/users/{}/'.format(reseller_name,
                                                                                     client_name,
                                                                                     email),
                                      content_type='application/json')
        self.assertFalse(request.status_code == 200)

    def test_two_applications(self):
        admin = User.objects.filter(username='admin').first()
        client_request = _get_client(admin.id)

        first_app_user = ClientUser.objects.filter().first()
        first_app_client = first_app_user.client
        first_app_reseller = first_app_client.reseller

        # create second application
        client_request.post('/v1/applications/',
                            json.dumps({'id': 'tricky_chicken_2'}),
                            content_type='application/json')

        self.assertTrue(ClientUser.objects.filter(email=first_app_user.email).count() == 2)
        self.assertTrue(Client.objects.filter(name=first_app_client.name).count() == 2)
        self.assertTrue(Reseller.objects.filter(name=first_app_reseller.name).count() == 2)

    def test_usage_limit(self):
        app = Application.objects.all().first()
        client_request = _get_client(app.owner.id)

        reseller = Reseller.objects.filter().first()

        client_limit = random.randint(0, reseller.limit)

        client_request.post('/v1/resellers/{}/clients/'.format(reseller.name),
                            json.dumps({'name': 'new_client', 'storage': {'limit': client_limit}}),
                            content_type='application/json')

        self.assertTrue(Client.objects.filter(name='new_client'))

        client_limit = random.randint(reseller.limit, reseller.limit + 100)

        client_request.post('/v1/resellers/{}/clients/'.format(reseller.name),
                            json.dumps({'name': 'new_client2', 'storage': {'limit': client_limit}}),
                            content_type='application/json')

        self.assertFalse(Client.objects.filter(name='new_client2'))

    def test_not_found_objects(self):
        app = Application.objects.all().first()
        client_request = _get_client(app.owner.id)

        reseller_code = client_request.get('/v1/resellers/not_found_reseller/',
                                           content_type='application/json').status_code

        reseller = Reseller.objects.all().first()

        client_code = client_request.get('/v1/resellers/{}/clients/'
                                         'not_found_client/'.format(reseller.name),
                                         content_type='application/json').status_code

        self.assertTrue(reseller_code == 404)
        self.assertTrue(client_code == 404)

    def test_jwt_token(self):
        reseller = Reseller.objects.all().first()
        client_request = _get_client(reseller.owner)

        client_user = ClientUser.objects.filter().first()
        res_name = reseller.name
        client_name = client_user.client.name
        email = client_user.email

        code = client_request.get('/v1/resellers/{}/clients/{}/users/{}/token/'.format(res_name,
                                                                                       client_name,
                                                                                       email),
                                  content_type='application/json').status_code
        self.assertTrue(code == 200)

    def test_app_403_creation(self):
        reseller = Reseller.objects.all().first()
        client_request = _get_client(reseller.owner)

        code = client_request.post('/v1/applications/',
                                   json.dumps({'id': 'tricky_chicken_2'}),
                                   content_type='application/json').status_code
        self.assertTrue(code == 403)

    def test_client_retrieve(self):
        admin = ClientUser.objects.filter(admin=True).first()
        client_name = admin.client.name
        reseller_name = admin.client.reseller.name

        app_request = _get_client(admin.client.reseller.application.owner)
        code = app_request.get('/v1/resellers/{}/clients/{}/'.format(reseller_name,
                                                                     client_name)).status_code
        self.assertTrue(code == 200)

        reseller_request = _get_client(admin.client.reseller.owner)

        code = reseller_request.get('/v1/resellers/{}/clients/{}/'.format(reseller_name,
                                                                          client_name)).status_code
        self.assertTrue(code == 200)

        user_request = _get_client(admin.user)

        code = user_request.get('/v1/resellers/{}/clients/{}/'.format(reseller_name,
                                                                      client_name)).status_code
        self.assertTrue(code == 200)

        not_admin = ClientUser.objects.filter(client=admin.client, admin=False).first()
        user_request = _get_client(not_admin.user)

        code = user_request.get('/v1/resellers/{}/clients/{}/'.format(reseller_name,
                                                                      client_name)).status_code
        self.assertTrue(code == 404)

    def test_user_mgmt_under_admin(self):
        admin = ClientUser.objects.filter(admin=True).first()
        client_name = admin.client.name
        reseller_name = admin.client.reseller.name
        request = _get_client(admin.user)

        # List
        code = request.get('/v1/resellers/{}/clients/{}/users/'.format(reseller_name,
                                                                       client_name)).status_code
        self.assertTrue(code == 200)

        # Retrieve
        user = ClientUser.objects.filter(admin=False, client=admin.client).first()
        url = '/v1/resellers/{}/clients/{}/users/{}/'
        code = request.get(url.format(reseller_name, client_name, user.email)).status_code
        self.assertTrue(code == 200)

        # Get user token
        url = '/v1/resellers/{}/clients/{}/users/{}/token/'
        code = request.get(url.format(reseller_name, client_name, user.email)).status_code
        self.assertTrue(code == 200)

        # Create
        code = request.post('/v1/resellers/{}/clients/{}/users/'.format(reseller_name,
                                                                        client_name),
                            json.dumps({'email': 'newuser@newclient.tld',
                                        'storage': {'limit': 3},
                                        'password': 'password'}),
                            content_type='application/json').status_code
        self.assertTrue(code == 201)

        # Delete
        url = '/v1/resellers/{}/clients/{}/users/{}/'
        code = request.delete(url.format(reseller_name, client_name, user.email)).status_code
        self.assertTrue(code == 204)
