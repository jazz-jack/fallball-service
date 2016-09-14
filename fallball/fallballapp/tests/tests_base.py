import json

from django.contrib.auth.models import User
from django.core.management import call_command
from django.shortcuts import get_object_or_404
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from fallballapp.models import Client, ClientUser, Reseller


def _get_client():
    """
    Returns request object with admin token
    """
    client = APIClient()
    # Get admin token and set up credentials
    admin = User.objects.filter(username='admin').first()
    if not admin:
        admin = User.objects.create_superuser('admin', 'admin@fallball.io', '1q2w3e')
    token = get_object_or_404(Token, user=admin)
    client.credentials(HTTP_AUTHORIZATION='Token {token}'.format(token=token.key))
    return client


class BaseTestCase(TestCase):
    """
    Test basic operations: model objects create/delete
    """

    # Check that resellers, clients, objects can be created and deleted
    @classmethod
    def setUpTestData(cls):
        cls.client_request = _get_client()

    def test_object_creation(self):
        # create_application
        self.client_request.post('/v1/applications/',
                                 json.dumps({'id': 'tricky_chicken'}),
                                 content_type='application/json')

        # create reseller
        self.client_request.post('/v1/resellers/',
                                 json.dumps({'id': 'test_reseller', 'application': 'tricky_chicken',
                                             'storage': {'limit': 200}}),
                                 content_type='application/json')
        # create client
        self.client_request.post('/v1/resellers/test_reseller/clients/',
                                 json.dumps({'id': 'test_client', 'storage': {'limit': 100}}),
                                 content_type='application/json')

        # create client admin user
        self.client_request.post('/v1/resellers/test_reseller/clients/test_client/users/',
                                 json.dumps({'id': 'test_admin_user@test.tld', 'admin': True,
                                             'storage': {'limit': 50}, 'password': '1q2w3e'}),
                                 content_type='application/json')

        # create client user
        self.client_request.post('/v1/resellers/test_reseller/clients/test_client/users/',
                                 json.dumps({'id': 'test_user@test.tld', 'admin': False,
                                             'storage': {'limit': 50}, 'password': '1q2w3e'}),
                                 content_type='application/json')

        # create client user without admin field
        self.client_request.post('/v1/resellers/test_reseller/clients/test_client/users/',
                                 json.dumps({'id': 'test_user2@test.tld',
                                             'storage': {'limit': 3}, 'password': '1q2w3e'}),
                                 content_type='application/json')

        # Check that all objects have been created correctly
        self.assertTrue(Reseller.objects.filter(id='test_reseller'))
        self.assertTrue(Client.objects.filter(id='test_client'))
        self.assertTrue(ClientUser.objects.filter(id='test_admin_user@test.tld', admin=True))
        self.assertTrue(ClientUser.objects.filter(id='test_user@test.tld', admin=False))
        self.assertTrue(ClientUser.objects.filter(id='test_user2@test.tld', admin=False))

    def test_object_recreation(self):
        self.client_request.post('/v1/resellers/',
                                 json.dumps({'id': 'RecreationReseller',
                                             'storage': {'limit': 200}}),
                                 content_type='application/json')
        self.client_request.delete('/v1/resellers/RecreationReseller',
                                   content_type='application/json')
        self.client_request.post('/v1/resellers/',
                                 json.dumps({'id': 'RecreationReseller',
                                             'storage': {'limit': 200}}),
                                 content_type='application/json')
