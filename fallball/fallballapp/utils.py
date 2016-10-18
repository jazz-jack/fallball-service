from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework_jwt.settings import api_settings
from rest_framework.response import Response

from fallballapp.models import Application, Reseller, ClientUser


def get_object_or_403(*args, **kwargs):
    try:
        result = get_object_or_404(*args, **kwargs)
    except Http404:
        raise PermissionDenied()
    return result


def get_app_username(app_id, username):
    return '{}.{}'.format(app_id, username)


def get_jwt_token(user):
    jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
    jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
    payload = jwt_payload_handler(user)
    return jwt_encode_handler(payload)


def get_model_object(user):
    application = Application.objects.filter(owner=user).first()
    if application:
        return application

    reseller = Reseller.objects.filter(owner=user).first()
    if reseller:
        return reseller

    client_user = ClientUser.objects.filter(owner=user).first()
    if client_user:
        return client_user

    return None


def get_application_of_object(obj):
    app = None
    if isinstance(obj, Application):
        return obj
    elif isinstance(obj, Reseller):
        return obj.application
    elif isinstance(obj, ClientUser):
        return obj.client.reseller.application

    return app


def is_superuser(f):
    def wrapper(*args, **kwargs):
        request = args[1]
        if request.user.is_superuser:
            return f(*args)
        return Response("Authorization failed", status=status.HTTP_403_FORBIDDEN)
    return wrapper


def is_application(f):
    def wrapper(*args, **kwargs):
        application = get_object_or_403(Application, owner=args[1].user)
        if not application:
            return Response("Authorization failed", status=status.HTTP_403_FORBIDDEN)
        return f(application=application, *args, **kwargs)
    return wrapper
