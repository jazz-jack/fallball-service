import base64
import json
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from fallballapp.models import Application, Reseller, Client, ClientUser, UNLIMITED


def _get_token_auth_client(user_id, accept='application/json'):
    client = APIClient(HTTP_ACCEPT=accept)
    token = Token.objects.filter(user_id=user_id).first()
    if not token:
        token = Token.objects.create(user_id=user_id)
    client.credentials(HTTP_AUTHORIZATION='Token {token}'.format(token=token.key))

    return client


def _get_basic_auth_client(user_id, password):
    auth = base64.b64encode('{}:{}'.format(user_id, password).encode('utf-8'))

    client = APIClient(HTTP_ACCEPT='application/json')
    client.credentials(HTTP_AUTHORIZATION='Basic {}'.format(auth.decode('utf-8')))

    return client


class BaseTestCase(TestCase):
    """
    Test basic operations: model objects create/delete
    """
    def setUp(self):
        admin = get_user_model().objects.filter(username='admin').first()
        if not admin:
            admin = get_user_model().objects.create_superuser(
                'admin',
                'admin@fallball.io',
                '1q2w3e')
        self.admin = admin
        client_request = _get_token_auth_client(admin.id)

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
        client_request = _get_token_auth_client(reseller.owner)
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
        client_request = _get_token_auth_client(app.owner.id)

        reseller = Reseller.objects.filter(application=app).first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request.post(url, json.dumps({'name': 'new_client', 'storage': {'limit': 200}}),
                            content_type='application/json')

        url = reverse('v1:users-list', kwargs={'reseller_name': reseller.name,
                                               'client_name': 'new_client'})
        client_request.post(url, json.dumps({'email': 'newuser@newclient.tld',
                                             'storage': {'limit': 30}}),
                            content_type='application/json')

        self.assertTrue(Client.objects.filter(name='new_client'))
        self.assertTrue(ClientUser.objects.filter(email='newuser@newclient.tld'))

    def test_deleting_by_app(self):
        app = Application.objects.all().first()
        client_request = _get_token_auth_client(app.owner.id)

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
        client_request = _get_token_auth_client(reseller.owner)

        client_user = ClientUser.objects.filter().first()
        client_name = client_user.client.name
        url = reverse('v1:users-detail', kwargs={'reseller_name': reseller.name,
                                                 'client_name': client_name,
                                                 'user_id': client_user.user_id})
        client_request.delete(url, content_type='application/json')
        self.assertFalse(ClientUser.objects.filter(email=client_user.email))

        url = reverse('v1:clients-detail', kwargs={'reseller_name': reseller.name,
                                                   'name': client_name})
        client_request.delete(url, content_type='application/json')
        self.assertFalse(Client.objects.filter(name=client_name))

    def test_duplicated_users(self):
        app = Application.objects.all().first()
        client_request = _get_token_auth_client(app.owner.id)

        client_user = ClientUser.objects.filter().first()
        user_id = client_user.user_id
        client_name = client_user.client.name
        reseller_name = client_user.client.reseller.name
        url = reverse('v1:users-detail', kwargs={'reseller_name': reseller_name,
                                                 'client_name': client_name,
                                                 'user_id': user_id})
        request = client_request.post(url, content_type='application/json')
        self.assertFalse(request.status_code == 200)

    def test_two_applications(self):
        admin = get_user_model().objects.filter(username='admin').first()
        client_request = _get_token_auth_client(admin.id)

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
        client_request = _get_token_auth_client(app.owner.id)

        reseller = Reseller.objects.filter(application=app).first()

        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request.post(url, json.dumps({'name': 'new_client',
                                             'storage': {'limit': reseller.limit - 10}}),
                            content_type='application/json')

        self.assertTrue(Client.objects.filter(name='new_client'))

        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request.post(url,
                            json.dumps({'name': 'new_client2',
                                        'storage': {'limit': reseller.limit + 100}}),
                            content_type='application/json')

        self.assertFalse(Client.objects.filter(name='new_client2'))

    def test_unlimited_storage(self):
        app = Application.objects.all().first()
        client_request = _get_token_auth_client(app.owner.id)

        # Test unlimited client created under unlimited reseller
        url = reverse('v1:resellers-list')
        res_code = client_request.post(url,
                                       json.dumps({'name': 'unlimited_res',
                                                   'storage': {'limit': UNLIMITED},
                                                   'rid': '6F9619FF-8B86-D011-B42D-00CF4FC964FF'}),
                                       content_type='application/json').status_code
        self.assertEqual(res_code, 201)

        url = reverse('v1:clients-list', kwargs={'reseller_name': 'unlimited_res'})
        client_code = client_request.post(url, json.dumps({'name': 'unlimited_client',
                                                           'storage': {'limit': UNLIMITED}}),
                                          content_type='application/json').status_code
        self.assertEqual(client_code, 201)

        url = reverse('v1:users-list', kwargs={'reseller_name': 'unlimited_res',
                                               'client_name': 'unlimited_client'})
        user_code = client_request.post(url, json.dumps({'email': 'email@domain.tld',
                                                         'storage': {'limit': 9000000}}),
                                        content_type='application/json').status_code
        self.assertEqual(user_code, 201)

        # Test unlimited client created under limited reseller
        url = reverse('v1:resellers-list')
        res_code = client_request.post(url,
                                       json.dumps({'name': 'limited_res',
                                                   'storage': {'limit': 300},
                                                   'rid': '7F9619FF-8B86-D011-B42D-00CF4FC964FF'}),
                                       content_type='application/json').status_code
        self.assertEqual(res_code, 201)

        url = reverse('v1:clients-list', kwargs={'reseller_name': 'limited_res'})
        client_code = client_request.post(url, json.dumps({'name': 'unlimited_client_2',
                                                           'storage': {'limit': UNLIMITED}}),
                                          content_type='application/json').status_code
        self.assertEqual(client_code, 201)

        url = reverse('v1:users-list', kwargs={'reseller_name': 'limited_res',
                                               'client_name': 'unlimited_client_2'})

        user_code = client_request.post(url, json.dumps({'email': 'email2@domain.tld',
                                                         'storage': {'limit': 9000000}}),
                                        content_type='application/json').status_code
        self.assertEqual(user_code, 400)

        user_code = client_request.post(url, json.dumps({'email': 'email3@domain.tld',
                                                         'storage': {'limit': 9}}),
                                        content_type='application/json').status_code
        self.assertEqual(user_code, 201)

    def test_not_found_objects(self):
        app = Application.objects.all().first()
        client_request = _get_token_auth_client(app.owner.id)

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
        client_request = _get_token_auth_client(reseller.owner)

        client_user = ClientUser.objects.filter().first()
        res_name = reseller.name
        client_name = client_user.client.name
        user_id = client_user.user_id

        url = reverse('v1:users-detail', kwargs={'reseller_name': res_name,
                                                 'client_name': client_name,
                                                 'user_id': user_id})
        code = client_request.get('{}{}'.format(url, 'token/'),
                                  content_type='application/json').status_code
        self.assertEqual(code, 200)

    def test_app_403_creation(self):
        reseller = Reseller.objects.all().first()
        client_request = _get_token_auth_client(reseller.owner)

        url = reverse('v1:applications-list')
        code = client_request.post(url, json.dumps({'id': 'tricky_chicken_2'}),
                                   content_type='application/json').status_code
        self.assertEqual(code, 403)

    def test_client_retrieve(self):
        admin = ClientUser.objects.filter(admin=True).first()
        client_name = admin.client.name
        reseller_name = admin.client.reseller.name

        app_request = _get_token_auth_client(admin.client.reseller.application.owner)
        url = reverse('v1:clients-detail', kwargs={'reseller_name': reseller_name,
                                                   'name': client_name})
        code = app_request.get(url).status_code
        self.assertEqual(code, 200)

        reseller_request = _get_token_auth_client(admin.client.reseller.owner)

        code = reseller_request.get(url).status_code
        self.assertEqual(code, 200)

        user_request = _get_token_auth_client(admin.owner)

        code = user_request.get(url).status_code
        self.assertEqual(code, 200)

        not_admin = ClientUser.objects.filter(client=admin.client, admin=False).first()
        user_request = _get_token_auth_client(not_admin.owner)

        code = user_request.get(url).status_code
        self.assertEqual(code, 404)

    def test_reseller_retrieve(self):
        admin = ClientUser.objects.filter(admin=True).first()
        app_request = _get_token_auth_client(admin.client.reseller.application.owner)
        url = reverse('v1:resellers-list')
        answer = app_request.get(url)
        self.assertEqual(answer.status_code, 200)
        self.assertTrue('token' in answer.data[0])

        reseller_request = _get_token_auth_client(admin.client.reseller.owner)
        code = reseller_request.get(url).status_code
        self.assertEqual(code, 200)
        self.assertTrue('token' in answer.data[0])

        user_request = _get_token_auth_client(admin.owner)
        answer = user_request.get(url)
        self.assertEqual(answer.status_code, 200)
        self.assertFalse('token' in answer.data[0])

        not_admin = ClientUser.objects.filter(client=admin.client, admin=False).first()
        user_request = _get_token_auth_client(not_admin.owner)
        code = user_request.get(url).status_code
        self.assertEqual(code, 200)

    def test_user_mgmt_under_admin(self):
        admin = ClientUser.objects.filter(admin=True).first()
        client_name = admin.client.name
        reseller_name = admin.client.reseller.name
        request = _get_token_auth_client(admin.owner)

        # List
        list_url = reverse('v1:users-list', kwargs={'reseller_name': reseller_name,
                                                    'client_name': client_name})

        code = request.get(list_url).status_code
        self.assertEqual(code, 200)

        # Retrieve
        user = ClientUser.objects.filter(admin=False, client=admin.client).first()
        url = reverse('v1:users-detail', kwargs={'reseller_name': reseller_name,
                                                 'client_name': client_name,
                                                 'user_id': user.user_id})
        code = request.get(url).status_code
        self.assertEqual(code, 200)

        # Get user token
        code = request.get('{}{}'.format(url, 'token/')).status_code
        self.assertEqual(code, 200)

        # Create
        code = request.post(list_url,
                            json.dumps({'email': 'newuser@newclient.tld',
                                        'storage': {'limit': 3}}),
                            content_type='application/json').status_code
        self.assertTrue(code == 201)

        # Delete
        code = request.delete(url).status_code
        self.assertEqual(code, 204)

    def test_login_link(self):
        user = ClientUser.objects.filter(admin=True).first()
        reseller_request = _get_token_auth_client(user.client.reseller.owner, accept='text/plain')
        url = reverse('v1:users-detail', kwargs={'reseller_name': user.client.reseller.name,
                                                 'client_name': user.client.name,
                                                 'user_id': user.user_id})
        # Get link for existing user
        resp = reseller_request.get('{}{}'.format(url, 'link/'))
        self.assertTrue('text/plain; charset=utf-8' in resp._headers['content-type'])
        self.assertEqual(resp.status_code, 200)
        assert 'token' in resp.data

        url = reverse('v1:users-detail', kwargs={'reseller_name': user.client.reseller.name,
                                                 'client_name': user.client.name,
                                                 'user_id': 'ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb'})
        # Get link for non-existing user
        resp = reseller_request.get('{}{}'.format(url, 'link/'))
        self.assertEqual(resp.status_code, 200)
        assert 'manual' in resp.data

    def test_update_user(self):
        admin = ClientUser.objects.filter(admin=True).first()
        user = ClientUser.objects.filter(admin=False, client=admin.client).first()
        request = _get_token_auth_client(admin.owner)

        url = reverse('v1:users-detail', kwargs={'reseller_name': user.client.reseller.name,
                                                 'client_name': user.client.name,
                                                 'user_id': user.user_id})

        # limit is reached
        resp = request.put(url, json.dumps({'email': user.email,
                                            'storage': {'limit': user.limit,
                                                        'usage': admin.client.limit + 1},
                                            'password': 'password'}),
                           content_type='application/json')

        self.assertEqual(resp.status_code, 400)

        # password and email successfully changed
        resp = request.put(url, json.dumps({'storage': {'limit': user.limit,
                                                        'usage': user.usage},
                                            'password': 'password2'}),
                           content_type='application/json')

        changed_user = ClientUser.objects.get(id=user.id)

        self.assertTrue(changed_user.owner.check_password('password2'))

        self.assertEqual(resp.status_code, 200)

        # storage and password are optional, if value not specified existing one is used
        user_before = ClientUser.objects.get(id=user.id)
        resp = request.put(url, json.dumps({'email': user.email}),
                           content_type='application/json')
        user_after = ClientUser.objects.get(id=user.id)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(user_before.password, user_after.password)
        self.assertEqual(user_before.limit, user_after.limit)
        self.assertEqual(user_before.usage, user_after.usage)
        self.assertEqual(user_before.admin, user_after.admin)

    def test_put_creation(self):
        admin = ClientUser.objects.filter(admin=True).first()
        request = _get_token_auth_client(admin.owner)
        user_id = uuid.uuid4()
        url = reverse('v1:users-detail', kwargs={'reseller_name': admin.client.reseller.name,
                                                 'client_name': admin.client.name,
                                                 'user_id': user_id})

        resp = request.put(url, json.dumps({'storage': {'limit': 5},
                                            'email': 'user@domain.tld'}),
                           content_type='application/json')

        self.assertTrue(ClientUser.objects.filter(user_id=user_id,
                                                  client=admin.client))

        self.assertEqual(resp.status_code, 201)

    def test_root_access(self):
        admin = ClientUser.objects.filter(admin=True).first()

        root = get_user_model().objects.filter(is_superuser=True)
        request = _get_token_auth_client(root)

        url = reverse('v1:resellers-detail', kwargs={'name': admin.client.reseller.name, })
        resp = request.get(url)
        self.assertEqual(resp.status_code, 404)

        url = reverse('v1:clients-detail', kwargs={'reseller_name': admin.client.reseller.name,
                                                   'name': admin.client.name, })
        resp = request.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_unauthorized_access(self):
        admin = ClientUser.objects.filter(admin=True).first()

        request = APIClient()

        url = reverse('v1:resellers-detail', kwargs={'name': admin.client.reseller.name, })
        resp = request.get(url)
        self.assertEqual(resp.status_code, 401)

        url = reverse('v1:clients-detail', kwargs={'reseller_name': admin.client.reseller.name,
                                                   'name': admin.client.name, })
        resp = request.get(url)
        self.assertEqual(resp.status_code, 401)

    def test_password_set(self):
        reseller = Reseller.objects.all().first()
        client = Client.objects.filter(reseller=reseller).first()
        request = _get_token_auth_client(reseller.owner)

        url = reverse('v1:users-list', kwargs={'reseller_name': reseller.name,
                                               'client_name': client.name})
        resp = request.post(url, json.dumps({'email': 'new@sunnyflowers.tld',
                                             'storage': {'limit': 5}}),
                            content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        user_id = resp.json()['user_id']

        url = reverse('v1:users-detail', kwargs={'reseller_name': reseller.name,
                                                 'client_name': client.name,
                                                 'user_id': user_id})
        resp = request.put(url, json.dumps({'email': 'new@sunnyflowers.tld',
                                            'storage': {'usage': 3, 'limit': 5},
                                            'password': 'newpassword'}),
                           content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        user = ClientUser.objects.get(client=client, email='new@sunnyflowers.tld').owner
        self.assertTrue(user.check_password('newpassword'))

    def test_sync_instantly_ready(self):
        app = Application.objects.all().first()
        app.async = False
        app.save()
        reseller = Reseller.objects.filter(application=app).first()

        client = Client.objects.create(name='sync_client', limit=100, reseller=reseller)

        self.assertEqual(client.status, Client.STATUS_READY)

    def test_async_ready_after_timeout(self):
        app = Application.objects.all().first()
        app.async = True
        app.save()
        reseller = Reseller.objects.filter(application=app).first()

        client = Client.objects.create(name='sync_client', limit=100, reseller=reseller)

        self.assertEqual(client.status, Client.STATUS_PROVISIONING)

        client.ready_at = timezone.now()
        client.save()

        client = Client.objects.filter(name='sync_client', reseller=reseller).first()

        self.assertEqual(client.status, Client.STATUS_READY)

    def test_app_set_async(self):
        app = Application.objects.all().first()
        app.async = False
        app.save()

        url = reverse('v1:applications-detail', kwargs={'pk': app.pk})
        request = _get_token_auth_client(self.admin.id)

        resp = request.put(url, json.dumps({'async': True}), content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        app = Application.objects.get(pk=app.pk)
        self.assertTrue(app.async)

        resp = request.put(url, json.dumps({'async': False}), content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        app = Application.objects.get(pk=app.pk)
        self.assertFalse(app.async)

    def test_postal_code_with_999_is_not_allowed(self):
        reseller = Reseller.objects.all().first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request = _get_token_auth_client(reseller.owner)
        resp = client_request.post(url, json.dumps({'name': 'new_client',
                                                    'storage': {'limit': 200},
                                                    'postal_code': '99912'
                                                    }),
                                   content_type='application/json')

        self.assertEqual(resp.status_code, 400)

        assert 'postal_code' in resp.json()

        self.assertEqual(resp.json()['postal_code']['code'], 'E1002')
        self.assertEqual(resp.json()['postal_code']['message'],
                         "Postal code can't start with 999")

    def test_postal_code_invalid(self):
        reseller = Reseller.objects.all().first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request = _get_token_auth_client(reseller.owner)
        resp = client_request.post(url, json.dumps({'name': 'new_client',
                                                    'storage': {'limit': 200},
                                                    'postal_code': 'invalid'
                                                    }),
                                   content_type='application/json')

        self.assertEqual(resp.status_code, 400)

        assert 'postal_code' in resp.json()

        self.assertEqual(resp.json()['postal_code']['code'], 'E1001')
        self.assertEqual(resp.json()['postal_code']['message'],
                         "Postal code must be a 5-digit number")

    def test_client_postal_code_is_saved(self):
        reseller = Reseller.objects.all().first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request = _get_token_auth_client(reseller.owner)
        client_request.post(url, json.dumps({'name': 'new_client',
                                             'storage': {'limit': 200},
                                             'postal_code': '12345'
                                             }),
                            content_type='application/json')

        client = Client.objects.filter(name='new_client').first()

        assert client is not None
        self.assertEqual(client.postal_code, '12345')

    def test_client_postal_code_is_null_if_not_provided(self):
        reseller = Reseller.objects.all().first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request = _get_token_auth_client(reseller.owner)
        resp = client_request.post(url, json.dumps({'name': 'new_client',
                                                    'storage': {'limit': 200}
                                                    }),
                                   content_type='application/json')

        self.assertEqual(resp.status_code, 201)

        client = Client.objects.filter(name='new_client').first()

        assert client is not None
        assert client.postal_code is None

    def test_creation_custom_profile(self):
        admin = ClientUser.objects.filter(admin=True).first()
        request = _get_token_auth_client(admin.owner)

        url = reverse('v1:users-list', kwargs={'reseller_name': admin.client.reseller.name,
                                               'client_name': admin.client.name})
        resp = request.post(url, json.dumps({'email': 'platinum@sunnyflowers.tld',
                                             'storage': {'limit': 5}, 'profile_type': 'PLATINUM'}),
                            content_type='application/json')
        self.assertEqual(resp.status_code, 201)

        created_user = ClientUser.objects.filter(email='platinum@sunnyflowers.tld').first()
        self.assertEqual(created_user.profile_type, 'PLATINUM')

    def test_change_user_profile_type(self):
        admin = ClientUser.objects.filter(admin=True).first()
        user = ClientUser.objects.filter(admin=False, client=admin.client).first()
        request = _get_token_auth_client(admin.owner)

        url = reverse('v1:users-detail', kwargs={'reseller_name': user.client.reseller.name,
                                                 'client_name': user.client.name,
                                                 'user_id': user.user_id})

        resp = request.put(url, json.dumps({'profile_type': 'BRILLIANT'}),
                           content_type='application/json')

        self.assertEqual(resp.status_code, 200)

        changed_user = ClientUser.objects.get(id=user.id)
        self.assertTrue(changed_user.profile_type, 'BRILLIANT')

    def test_get_users_by_type(self):
        admin = ClientUser.objects.filter(admin=True).first()
        user = ClientUser.objects.filter(admin=False, client=admin.client).first()
        user.profile_type = 'BRONZE'
        user.save(update_fields=['profile_type'])

        request = _get_token_auth_client(admin.owner)

        url = reverse('v1:clients-detail', kwargs={'reseller_name': admin.client.reseller.name,
                                                   'name': admin.client.name, })
        resp = request.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['users_by_type']['BRONZE'], 1)

    def test_basic_auth_by_email(self):
        app = Application.objects.all().first()

        client_user = ClientUser.objects.filter().first()
        client_user.owner.set_password('123qwe123')
        client_user.owner.save()

        user_id = '{}.{}'.format(app.id, client_user.email)

        client_request = _get_basic_auth_client(user_id, '123qwe123')

        url = reverse('v1:ui_users-list')
        response = client_request.get(url)

        self.assertEqual(response.status_code, 200)

    def test_basic_auth_by_email_user_does_not_exist(self):
        app = Application.objects.all().first()

        user_id = '{}.{}'.format(app.id, 'wrong@email.tld')

        client_request = _get_basic_auth_client(user_id, '123qwe123')

        url = reverse('v1:ui_users-list')
        response = client_request.get(url)

        self.assertEqual(response.status_code, 401)

    def test_basic_auth_by_email_wrong_app(self):
        client_user = ClientUser.objects.filter().first()

        user_id = '{}.{}'.format('wrong_app', client_user.email)

        client_request = _get_basic_auth_client(user_id, '123qwe123')

        url = reverse('v1:ui_users-list')
        response = client_request.get(url)

        self.assertEqual(response.status_code, 401)

    def test_superadmin_always_created_with_zero_limit(self):
        reseller = Reseller.objects.all().first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request = _get_token_auth_client(reseller.owner)
        client_request.post(url, json.dumps({'name': 'new_client', 'storage': {'limit': 200}}),
                            content_type='application/json')

        url = reverse('v1:users-list', kwargs={'reseller_name': reseller.name,
                                               'client_name': 'new_client'})
        client_request.post(url, json.dumps({'email': 'newuser@newclient.tld',
                                             'storage': {'limit': 30},
                                             'superadmin': True,
                                             'password': 'password'}),
                            content_type='application/json')

        self.assertEqual(ClientUser.objects.get(email='newuser@newclient.tld').limit, 0)

    def test_superadmin_does_not_affect_users_count(self):
        reseller = Reseller.objects.all().first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request = _get_token_auth_client(reseller.owner)
        client_request.post(url, json.dumps({'name': 'new_client', 'storage': {'limit': 200}}),
                            content_type='application/json')

        url = reverse('v1:users-list', kwargs={'reseller_name': reseller.name,
                                               'client_name': 'new_client'})
        client_request.post(url, json.dumps({'email': 'newuser@newclient.tld',
                                             'storage': {'limit': 30},
                                             'superadmin': True,
                                             'password': 'password'}),
                            content_type='application/json')

        self.assertTrue(ClientUser.objects.get(email='newuser@newclient.tld'))

        url = reverse('v1:clients-detail', kwargs={'reseller_name': reseller.name,
                                                   'name': 'new_client'})

        resp = client_request.get(url)

        self.assertEqual(resp.json()['users_amount'], 0)
        self.assertTrue(all(value == 0 for value in resp.json()['users_by_type'].values()))

    def test_superadmin_invisible_in_get_users_list(self):
        reseller = Reseller.objects.all().first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request = _get_token_auth_client(reseller.owner)
        client_request.post(url, json.dumps({'name': 'new_client', 'storage': {'limit': 200}}),
                            content_type='application/json')

        url = reverse('v1:users-list', kwargs={'reseller_name': reseller.name,
                                               'client_name': 'new_client'})
        client_request.post(url, json.dumps({'email': 'newuser@newclient.tld',
                                             'storage': {'limit': 30},
                                             'superadmin': True,
                                             'password': 'password'}),
                            content_type='application/json')

        self.assertTrue(ClientUser.objects.get(email='newuser@newclient.tld'))

        resp = client_request.get(url)

        self.assertEquals(resp.status_code, 200)
        self.assertEquals(len(resp.json()), 0)

    def test_country_and_environment_are_read_only_list(self):
        reseller = Reseller.objects.all().first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request = _get_token_auth_client(reseller.owner)
        client_request.post(url, json.dumps({'name': 'new_client', 'storage': {'limit': 200},
                                             'environment': 'test', 'country': 'US'}),
                            content_type='application/json')

        url = reverse('v1:clients-detail', kwargs={'reseller_name': reseller.name,
                                                   'name': 'new_client'})
        client_request.put(url, json.dumps({'name': 'new_client', 'storage': {'limit': 200},
                                            'country': 'CA', 'environment': 'production'}),
                           content_type='application/json')

        resp = client_request.get(url)
        self.assertEquals(resp.status_code, 200)

        client = resp.json()

        self.assertEquals(client['country'], 'US')
        self.assertEquals(client['environment'], 'test')
