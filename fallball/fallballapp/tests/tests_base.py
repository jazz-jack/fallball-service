import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from fallballapp.models import Application, Reseller, Client, ClientUser, UNLIMITED


def _get_client(user_id, accept='application/json'):
    """
    Returns request object with admin token
    """
    client = APIClient(HTTP_ACCEPT=accept)
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
        admin = get_user_model().objects.filter(username='admin').first()
        if not admin:
            admin = get_user_model().objects.create_superuser(
                'admin',
                'admin@fallball.io',
                '1q2w3e')
        self.admin = admin
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
                                             'storage': {'limit': 30}}),
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
        admin = get_user_model().objects.filter(username='admin').first()
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
        client_request = _get_client(app.owner.id)

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

        user_request = _get_client(admin.owner)

        code = user_request.get(url).status_code
        self.assertEqual(code, 200)

        not_admin = ClientUser.objects.filter(client=admin.client, admin=False).first()
        user_request = _get_client(not_admin.owner)

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

        user_request = _get_client(admin.owner)
        answer = user_request.get(url)
        self.assertEqual(answer.status_code, 200)
        self.assertFalse('token' in answer.data[0])

        not_admin = ClientUser.objects.filter(client=admin.client, admin=False).first()
        user_request = _get_client(not_admin.owner)
        code = user_request.get(url).status_code
        self.assertEqual(code, 200)

    def test_user_mgmt_under_admin(self):
        admin = ClientUser.objects.filter(admin=True).first()
        client_name = admin.client.name
        reseller_name = admin.client.reseller.name
        request = _get_client(admin.owner)

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
                                        'storage': {'limit': 3}}),
                            content_type='application/json').status_code
        self.assertTrue(code == 201)

        # Delete
        code = request.delete(url).status_code
        self.assertEqual(code, 204)

    def test_login_link(self):
        user = ClientUser.objects.filter(admin=True).first()
        reseller_request = _get_client(user.client.reseller.owner, accept='text/plain')
        url = reverse('v1:users-detail', kwargs={'reseller_name': user.client.reseller.name,
                                                 'client_name': user.client.name,
                                                 'email': user.email})
        # Get link for existing user
        resp = reseller_request.get('{}{}'.format(url, 'link/'))
        self.assertTrue('text/plain; charset=utf-8' in resp._headers['content-type'])
        self.assertEqual(resp.status_code, 200)
        assert 'token' in resp.data

        url = reverse('v1:users-detail', kwargs={'reseller_name': user.client.reseller.name,
                                                 'client_name': user.client.name,
                                                 'email': 'random-user@does-not-exist.local'})
        # Get link for non-existing user
        resp = reseller_request.get('{}{}'.format(url, 'link/'))
        self.assertEqual(resp.status_code, 200)
        assert 'manual' in resp.data

    def test_update_user(self):
        admin = ClientUser.objects.filter(admin=True).first()
        user = ClientUser.objects.filter(admin=False, client=admin.client).first()
        request = _get_client(admin.owner)

        url = reverse('v1:users-detail', kwargs={'reseller_name': user.client.reseller.name,
                                                 'client_name': user.client.name,
                                                 'email': user.email})

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
        request = _get_client(admin.owner)

        url = reverse('v1:users-detail', kwargs={'reseller_name': admin.client.reseller.name,
                                                 'client_name': admin.client.name,
                                                 'email': 'new@sunnyflowers.tld'})

        resp = request.put(url, json.dumps({'storage': {'limit': 5}}),
                           content_type='application/json')

        self.assertTrue(ClientUser.objects.filter(email='new@sunnyflowers.tld',
                                                  client=admin.client))

        self.assertEqual(resp.status_code, 201)

    def test_root_access(self):
        admin = ClientUser.objects.filter(admin=True).first()

        root = get_user_model().objects.filter(is_superuser=True)
        request = _get_client(root)

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
        request = _get_client(reseller.owner)

        url = reverse('v1:users-list', kwargs={'reseller_name': reseller.name,
                                               'client_name': client.name})
        resp = request.post(url, json.dumps({'email': 'new@sunnyflowers.tld',
                                             'storage': {'limit': 5}}),
                            content_type='application/json')
        self.assertEqual(resp.status_code, 201)

        url = reverse('v1:users-detail', kwargs={'reseller_name': reseller.name,
                                                 'client_name': client.name,
                                                 'email': 'new@sunnyflowers.tld'})
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
        request = _get_client(self.admin.id)

        resp = request.put(url, json.dumps({'async': True}), content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        app = Application.objects.get(pk=app.pk)
        self.assertTrue(app.async)

        resp = request.put(url, json.dumps({'async': False}), content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        app = Application.objects.get(pk=app.pk)
        self.assertFalse(app.async)

    def test_email_with_dot_not_allowed(self):
        reseller = Reseller.objects.all().first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request = _get_client(reseller.owner)
        resp = client_request.post(url, json.dumps({'name': 'new_client',
                                                    'storage': {'limit': 200},
                                                    'email': 'new.client@fallball.io'
                                                    }),
                                   content_type='application/json')

        self.assertEqual(resp.status_code, 400)
        assert 'email' in resp.json()

    def test_client_email_is_saved(self):
        reseller = Reseller.objects.all().first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request = _get_client(reseller.owner)
        client_request.post(url, json.dumps({'name': 'new_client',
                                             'storage': {'limit': 200},
                                             'email': 'new_client@fallball.io'
                                             }),
                            content_type='application/json')

        client = Client.objects.filter(name='new_client').first()

        assert client is not None
        self.assertEqual(client.email, 'new_client@fallball.io')

    def test_client_email_is_null_if_not_provided(self):
        reseller = Reseller.objects.all().first()
        url = reverse('v1:clients-list', kwargs={'reseller_name': reseller.name})
        client_request = _get_client(reseller.owner)
        resp = client_request.post(url, json.dumps({'name': 'new_client',
                                                    'storage': {'limit': 200}
                                                    }),
                                   content_type='application/json')

        self.assertEqual(resp.status_code, 201)

        client = Client.objects.filter(name='new_client').first()

        assert client is not None
        assert client.email is None
