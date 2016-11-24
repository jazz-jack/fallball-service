from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from fallballapp.models import Application

def load_data(apps, schema_editor):
    user_admin, created = get_user_model().objects.get_or_create(
        username='admin',
        password='pbkdf2_sha256$24000$ZVxkeukDOSaR$BkbfzKABp5MTWFALbWbggsunbYjTWYn8G/+tWMktZZg=',
        is_superuser=True,
        is_staff=True)

    Token.objects.get_or_create(
        pk=settings.ADMIN_AUTH_TOKEN,
        user=user_admin)

    user_app, created = get_user_model().objects.get_or_create(
        username='new_app',
        is_superuser=False,
        is_staff=False)

    Application.objects.get_or_create(pk='new_app', owner_id=user_app.id)