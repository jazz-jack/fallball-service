from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework_jwt.settings import api_settings
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN
from rest_framework.response import Response

from fallballapp.models import Application, Reseller, Client, ClientUser, UNLIMITED


def get_object_or_403(*args, **kwargs):
    try:
        result = get_object_or_404(*args, **kwargs)
    except Http404:
        raise PermissionDenied()
    return result


def get_app_username(app_id, username):
    return u'{}.{}'.format(app_id, username)


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


def get_user_context(f):
    def wrapper(*args, **kwargs):
        request = args[1]

        # check if context already exists
        if all(field in kwargs for field in ('application', 'reseller', 'client')):
            context = {}
            for field in ('application', 'reseller', 'client'):
                context[field] = kwargs.pop(field)
            return f(application=context['application'], reseller=context['reseller'],
                     client=context['client'], *args, **kwargs)

        application = Application.objects.filter(owner=request.user).first()
        if application:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               application=application).first()
        else:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               owner=request.user).first()
            if not reseller:
                client_user = get_object_or_404(ClientUser, owner=request.user)
                if client_user.admin is True or f.__name__ in ('retrieve', 'update'):
                    reseller = client_user.client.reseller
                else:
                    return Response("Authorization failed", status=HTTP_403_FORBIDDEN)

                if not client_user.client.name == kwargs['client_name']:
                    return Response("Authorization failed", status=HTTP_403_FORBIDDEN)

            application = reseller.application

        if not reseller:
            return Response("Such reseller is not found", status=HTTP_404_NOT_FOUND)

        client = Client.objects.filter(reseller=reseller, name=kwargs['client_name']).first()

        return f(application=application, reseller=reseller, client=client, *args, **kwargs)
    return wrapper


def free_space(owner):
    if int(owner.limit) is not UNLIMITED:
        return int(owner.limit - owner.get_usage())
    elif isinstance(owner, Reseller):
        return UNLIMITED
    elif isinstance(owner, Client):
        return free_space(owner.reseller)
    return None
