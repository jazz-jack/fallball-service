from django.utils.translation import ugettext_lazy

from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed

from fallballapp.models import ClientUser


class EmailBasicAuthentication(BasicAuthentication):
    def authenticate_credentials(self, userid, password):
        app_with_email = userid.partition('.')

        app, email = app_with_email[0], app_with_email[2]

        user_obj = ClientUser.objects.filter(email=email).first()

        if not user_obj or user_obj.client.reseller.application.id != app:
            raise AuthenticationFailed(ugettext_lazy("Invalid username/password."))

        user_id = '{}.{}'.format(app, user_obj.user_id)

        return super(EmailBasicAuthentication, self).authenticate_credentials(user_id, password)
