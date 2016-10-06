import json
import random

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
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
        url = reverse('v1:applications-list')
        client_request.post(url,
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
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request = _get_client(reseller.owner)
        client_request.post(url, json.dumps({'name': 'new_client', 'storage': {'limit': 200}}),
                            content_type='application/json')

        url = reverse('v1:users-list', kwargs={'reseller_name': reseller.name,
                                               'client_name': 'new_client'})
        client_request.post(url, json.dumps({'email': 'newuser@newclient.tld',
                                             'storage': {'limit': 30},
                                             'password': 'password'}),
                            content_type='application/json')

        self.assertTrue(Client.objects.filter(name='new_client'))
        self.assertTrue(ClientUser.objects.filter(email='newuser@newclient.tld'))

    def test_creation_under_app(self):
        app = Application.objects.all().first()
        client_request = _get_client(app.owner.id)

        reseller = Reseller.objects.filter(application=app).first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request.post(url, json.dumps({'name': 'new_client', 'storage': {'limit': 200}}),
                            content_type='application/json')

        url = reverse('v1:users-list', kwargs={'reseller_name': reseller.name,
                                               'client_name': 'new_client'})
        client_request.post(url, json.dumps({'email': 'newuser@newclient.tld',
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
        url = reverse('v1:clients-detail', kwargs={'reseller_name': reseller_name,
                                                   'name': client.name})
        client_request.delete(url, content_type='application/json')
        self.assertFalse(Client.objects.filter(name=client.name))

        url = reverse('v1:resellers-detail', kwargs={'name': reseller_name})
        client_request.delete(url, content_type='application/json')
        self.assertFalse(Reseller.objects.filter(name=reseller_name))

    def test_deleting_by_reseller(self):
        reseller = Reseller.objects.all().first()
        client_request = _get_client(reseller.owner)

        client_user = ClientUser.objects.filter().first()
        client_name = client_user.client.name
        url = reverse('v1:users-detail', kwargs={'reseller_name': reseller.name,
                                                 'client_name': client_name,
                                                 'email': client_user.email})
        client_request.delete(url, content_type='application/json')
        self.assertFalse(ClientUser.objects.filter(email=client_user.email))

        url = reverse('v1:clients-detail', kwargs={'reseller_name': reseller.name,
                                                   'name': client_name})
        client_request.delete(url, content_type='application/json')
        self.assertFalse(Client.objects.filter(name=client_name))

    def test_duplicated_users(self):
        app = Application.objects.all().first()
        client_request = _get_client(app.owner.id)

        client_user = ClientUser.objects.filter().first()
        email = client_user.email
        client_name = client_user.client.name
        reseller_name = client_user.client.reseller.name
        url = reverse('v1:users-detail', kwargs={'reseller_name': reseller_name,
                                                 'client_name': client_name,
                                                 'email': email})
        request = client_request.post(url, content_type='application/json')
        self.assertFalse(request.status_code == 200)

    def test_two_applications(self):
        admin = User.objects.filter(username='admin').first()
        client_request = _get_client(admin.id)

        first_app_user = ClientUser.objects.filter().first()
        first_app_client = first_app_user.client
        first_app_reseller = first_app_client.reseller

        # create second application
        url = reverse('v1:applications-list')
        client_request.post(url, json.dumps({'id': 'tricky_chicken_2'}),
                            content_type='application/json')

        self.assertEqual(ClientUser.objects.filter(email=first_app_user.email).count(), 2)
        self.assertEqual(Client.objects.filter(name=first_app_client.name).count(), 2)
        self.assertEqual(Reseller.objects.filter(name=first_app_reseller.name).count(), 2)

    def test_usage_limit(self):
        app = Application.objects.all().first()
        client_request = _get_client(app.owner.id)

        reseller = Reseller.objects.filter().first()

        client_limit = random.randint(0, reseller.limit)

        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request.post(url, json.dumps({'name': 'new_client',
                                             'storage': {'limit': client_limit}}),
                            content_type='application/json')

        self.assertTrue(Client.objects.filter(name='new_client'))

        client_limit = random.randint(reseller.limit, reseller.limit + 100)

        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request.post(url,
                            json.dumps({'name': 'new_client2', 'storage': {'limit': client_limit}}),
                            content_type='application/json')

        self.assertFalse(Client.objects.filter(name='new_client2'))

    def test_not_found_objects(self):
        app = Application.objects.all().first()
        client_request = _get_client(app.owner.id)

        url = reverse('v1:resellers-detail', kwargs={'name': 'not_found_reseller'})
        reseller_code = client_request.get(url, content_type='application/json').status_code

        reseller = Reseller.objects.all().first()
        url = reverse('v1:clients-detail', kwargs={'reseller_name': reseller.name,
                                                   'name': 'not_found_client'})
        client_code = client_request.get(url, content_type='application/json').status_code

        self.assertEqual(reseller_code, 404)
        self.assertEqual(client_code, 404)

    def test_jwt_token(self):
        reseller = Reseller.objects.all().first()
        client_request = _get_client(reseller.owner)

        client_user = ClientUser.objects.filter().first()
        res_name = reseller.name
        client_name = client_user.client.name
        email = client_user.email

        url = reverse('v1:users-detail', kwargs={'reseller_name': res_name,
                                                 'client_name': client_name,
                                                 'email': email})
        code = client_request.get('{}{}'.format(url, 'token/'),
                                  content_type='application/json').status_code
        self.assertEqual(code, 200)

    def test_app_403_creation(self):
        reseller = Reseller.objects.all().first()
        client_request = _get_client(reseller.owner)

        url = reverse('v1:applications-list')
        code = client_request.post(url, json.dumps({'id': 'tricky_chicken_2'}),
                                   content_type='application/json').status_code
        self.assertEqual(code, 403)

    def test_client_retrieve(self):
        admin = ClientUser.objects.filter(admin=True).first()
        client_name = admin.client.name
        reseller_name = admin.client.reseller.name

        app_request = _get_client(admin.client.reseller.application.owner)
        url = reverse('v1:clients-detail', kwargs={'reseller_name': reseller_name,
                                                   'name': client_name})
        code = app_request.get(url).status_code
        self.assertEqual(code, 200)

        reseller_request = _get_client(admin.client.reseller.owner)

        code = reseller_request.get(url).status_code
        self.assertEqual(code, 200)

        user_request = _get_client(admin.user)

        code = user_request.get(url).status_code
        self.assertEqual(code, 200)

        not_admin = ClientUser.objects.filter(client=admin.client, admin=False).first()
        user_request = _get_client(not_admin.user)

        code = user_request.get(url).status_code
        self.assertEqual(code, 404)

    def test_reseller_retrieve(self):
        admin = ClientUser.objects.filter(admin=True).first()
        app_request = _get_client(admin.client.reseller.application.owner)
        url = reverse('v1:resellers-list')
        answer = app_request.get(url)
        self.assertEqual(answer.status_code, 200)
        self.assertTrue('token' in answer.data[0])

        reseller_request = _get_client(admin.client.reseller.owner)
        code = reseller_request.get(url).status_code
        self.assertEqual(code, 200)
        self.assertTrue('token' in answer.data[0])

        user_request = _get_client(admin.user)
        answer = user_request.get(url)
        self.assertEqual(answer.status_code, 200)
        self.assertFalse('token' in answer.data[0])

        not_admin = ClientUser.objects.filter(client=admin.client, admin=False).first()
        user_request = _get_client(not_admin.user)
        code = user_request.get(url).status_code
        self.assertEqual(code, 404)

    def test_user_mgmt_under_admin(self):
        admin = ClientUser.objects.filter(admin=True).first()
        client_name = admin.client.name
        reseller_name = admin.client.reseller.name
        request = _get_client(admin.user)

        # List
        list_url = reverse('v1:users-list', kwargs={'reseller_name': reseller_name,
                                                    'client_name': client_name})
        code = request.get(list_url).status_code
        self.assertEqual(code, 200)

        # Retrieve
        user = ClientUser.objects.filter(admin=False, client=admin.client).first()
        url = reverse('v1:users-detail', kwargs={'reseller_name': reseller_name,
                                                 'client_name': client_name,
                                                 'email': user.email})
        code = request.get(url).status_code
        self.assertEqual(code, 200)

        # Get user token
        code = request.get('{}{}'.format(url, 'token/')).status_code
        self.assertEqual(code, 200)

        # Create
        code = request.post(list_url,
                            json.dumps({'email': 'newuser@newclient.tld',
                                        'storage': {'limit': 3},
                                        'password': 'password'}),
                            content_type='application/json').status_code
        self.assertTrue(code == 201)

        # Delete
        code = request.delete(url).status_code
        self.assertEqual(code, 204)
