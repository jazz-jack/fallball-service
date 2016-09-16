import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from fallballapp.models import Application


def _get_client():
    """
    Returns request object with admin token
    """
    client = APIClient()
    # Get admin token and set up credentials
    admin = User.objects.filter(username='admin').first()
    if not admin:
        admin = User.objects.create_superuser('admin', 'admin@fallball.io', '1q2w3e')

    token = Token.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION='Token {token}'.format(token=token.key))
    return client


class BaseTestCase(TestCase):
    """
    Test basic operations: model objects create/delete
    """

    @classmethod
    def setUpTestData(cls):
        cls.client_request = _get_client()

    def test_object_creation(self):
        # create_application
        self.client_request.post('/v1/applications/',
                                 json.dumps({'id': 'tricky_chicken'}),
                                 content_type='application/json')

        # create second application
        self.client_request.post('/v1/applications/',
                                 json.dumps({'id': 'tricky_chicken_2'}),
                                 content_type='application/json')

        self.assertTrue(Application.objects.filter(id='tricky_chicken'))
        self.assertTrue(Application.objects.filter(id='tricky_chicken_2'))
