from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token


def create_admin(apps, schema_editor):
    admin = get_user_model().objects.create(
        username='admin',
        password='pbkdf2_sha256$24000$ZVxkeukDOSaR$BkbfzKABp5MTWFALbWbggsunbYjTWYn8G/+tWMktZZg=',
        is_superuser=True,
        is_staff=True)

    Token.objects.create(
        pk=settings.ADMIN_AUTH_TOKEN,
        user=admin)
