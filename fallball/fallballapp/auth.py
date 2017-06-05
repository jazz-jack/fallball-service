import base64

from django.utils.translation import ugettext_lazy

from rest_framework import HTTP_HEADER_ENCODING
from rest_framework.authentication import BasicAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from fallballapp.models import ClientUser


class EmailBasicAuthentication(BasicAuthentication):
    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'basic':
            return None

        if len(auth) == 1:
            msg = ugettext_lazy("Invalid basic header. No credentials provided.")
            raise AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = ugettext_lazy("Invalid basic header. "
                                "Credentials string should not contain spaces.")
            raise AuthenticationFailed(msg)

        try:
            auth_parts = base64.b64decode(auth[1]).decode(HTTP_HEADER_ENCODING).partition(':')
        except (TypeError, UnicodeDecodeError):
            msg = ugettext_lazy("Invalid basic header. "
                                "Credentials not correctly base64 encoded.")
            raise AuthenticationFailed(msg)

        email_with_app_prefix, password = auth_parts[0], auth_parts[2]

        email_with_app_prefix_parts = email_with_app_prefix.partition('.')

        app, email = email_with_app_prefix_parts[0], email_with_app_prefix_parts[2]

        user_obj = ClientUser.objects.filter(email=email).first()

        if not user_obj:
            raise AuthenticationFailed(ugettext_lazy("Invalid username/password."))

        user_id = '{}.{}'.format(app, user_obj.user_id)

        return self.authenticate_credentials(user_id, password)
