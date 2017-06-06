import pkg_resources

from django.contrib.auth import get_user_model
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import detail_route
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

try:
    import urllib.parse as urlparse
    from urllib.parse import urlencode
except ImportError:
    import urlparse
    from urllib import urlencode

from fallballapp.auth import EmailBasicAuthentication
from fallballapp.middleware import logger
from fallballapp.models import Application, Client, ClientUser, Reseller, UNLIMITED
from fallballapp.renderers import PlainTextRenderer
from fallballapp.serializers import (ApplicationSerializer, ApplicationPutSerializer,
                                     ClientSerializer, ClientUserSerializer, ResellerSerializer,
                                     ResellerNameSerializer, UserAuthorizationSerializer)
from fallballapp.utils import (get_app_username, get_object_or_403, get_jwt_token,
                               is_superuser, is_application, get_user_context, free_space)


class Description(APIView):
    def get(self, *args, **kwargs):
        env = pkg_resources.Environment()
        res = env._distmap.get('fallball', [None])[0]
        version = res.version if res else ''
        return Response({'description': 'Fallball - File sharing, that everyone learns',
                         'version': version})


class ApplicationViewSet(ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = Application.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return ApplicationPutSerializer
        return ApplicationSerializer

    @is_superuser
    def create(self, request, *args, **kwargs):
        return ModelViewSet.create(self, request, *args, **kwargs)

    @is_superuser
    def list(self, request, *args, **kwargs):
        return ModelViewSet.list(self, request, *args, **kwargs)

    @is_superuser
    def retrieve(self, request, *args, **kwargs):
        return ModelViewSet.retrieve(self, request, *args, **kwargs)

    @is_superuser
    def destroy(self, request, *args, **kwargs):
        return ModelViewSet.destroy(self, request, *args, **kwargs)

    @is_superuser
    def update(self, request, *args, **kwargs):
        return ModelViewSet.update(self, request, *args, partial=True, **kwargs)


class ResellerViewSet(ModelViewSet):
    authentication_classes = (TokenAuthentication, JSONWebTokenAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = ResellerSerializer
    queryset = Reseller.objects.all()
    lookup_field = 'name'

    @is_application
    def create(self, request, *args, **kwargs):
        request.data['application'] = kwargs['application']
        return ModelViewSet.create(self, request, *args, **kwargs)

    @is_application
    def destroy(self, request, *args, **kwargs):
        Reseller.objects.filter(name=kwargs['name'],
                                application=kwargs['application']).delete()
        return Response('Reseller has been deleted', status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        application = Application.objects.filter(owner=request.user).first()
        if application:
            resellers = Reseller.objects.filter(application=application)
        else:
            resellers = Reseller.objects.filter(owner=request.user)
            if not resellers:
                client_user = ClientUser.objects.filter(owner=request.user).first()
                if not client_user:
                    return Response("Resellers do not exist for such account",
                                    status=HTTP_404_NOT_FOUND)

                queryset = [client_user.client.reseller, ]
                serializer = ResellerNameSerializer(queryset, many=True)
                return Response(serializer.data)

        queryset = resellers
        serializer = ResellerSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        application = Application.objects.filter(owner=request.user).first()
        if application:
            reseller = get_object_or_404(Reseller, name=kwargs['name'],
                                         application=application)
        else:
            reseller = get_object_or_404(Reseller, name=kwargs['name'],
                                         owner=request.user)
        queryset = (reseller,)
        serializer = ResellerSerializer(queryset, many=True)
        return Response(serializer.data[0])


class ClientViewSet(ModelViewSet):
    """
    ViewSet which manages clients
    """
    queryset = Client.objects.all().order_by('-id')
    serializer_class = ClientSerializer
    authentication_classes = (TokenAuthentication, JSONWebTokenAuthentication)
    permission_classes = (IsAuthenticated,)
    lookup_field = 'name'

    def create(self, request, *args, **kwargs):
        """
        Create new reseller client
        """
        application = Application.objects.filter(owner=request.user).first()
        if application:
            reseller = get_object_or_403(Reseller, name=kwargs['reseller_name'],
                                         application=application)
        else:
            reseller = get_object_or_403(Reseller, name=kwargs['reseller_name'],
                                         owner=request.user)
        if not Client.objects.filter(reseller=reseller,
                                     name=request.data['name']):

            # Check if there is a free space for new client or storage is unlimited
            space = free_space(reseller)
            if space >= request.data['storage']['limit'] or reseller.limit is UNLIMITED:
                # Every client should belong to particular reseller
                request.data['reseller'] = reseller
                return ModelViewSet.create(self, request, *args, **kwargs)
            return Response("Reseller limit is reached", status=status.HTTP_400_BAD_REQUEST)
        return Response("Such client already exists", status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, **kwargs):
        """
        Return list of clients which owned by particular reseller
        """
        # If application token is provided we just get reseller for this application from the db
        # If reseller token is provided we need to check that clients are owned by this reseller
        application = Application.objects.filter(owner=request.user).first()
        if application:
            reseller = get_object_or_403(Reseller, name=kwargs['reseller_name'],
                                         application=application)
        else:
            reseller = get_object_or_403(Reseller, name=kwargs['reseller_name'],
                                         owner=request.user)

        queryset = Client.objects.filter(reseller=reseller)
        serializer = ClientSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Return particular client which owned by particular reseller
        """
        application = Application.objects.filter(owner=request.user).first()
        if application:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               application=application).first()
        else:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               owner=request.user).first()
            if not reseller:
                admin = ClientUser.objects.filter(owner=request.user, admin=True).first()
                if not admin:
                    return Response("Client does not exist", status=HTTP_404_NOT_FOUND)
                if not admin.client.name == kwargs['name']:
                    return Response("Authorization failed", status=status.HTTP_403_FORBIDDEN)
                reseller = admin.client.reseller

        client = Client.objects.filter(reseller=reseller, name=kwargs['name']).first()
        if not client:
            return Response("Client does not exist", status=status.HTTP_404_NOT_FOUND)
        queryset = (client, )
        serializer = ClientSerializer(queryset, many=True)
        return Response(serializer.data[0])

    def destroy(self, request, *args, **kwargs):
        application = Application.objects.filter(owner=request.user).first()
        if application:
            reseller = get_object_or_403(Reseller, name=kwargs['reseller_name'],
                                         application=application)
        else:
            reseller = get_object_or_403(Reseller, name=kwargs['reseller_name'],
                                         owner=request.user)
        client = Client.objects.filter(name=kwargs['name'], reseller=reseller).first()
        if client:
            client.delete()
            return Response('Client has been deleted', status=status.HTTP_204_NO_CONTENT)
        return Response('Such client does not exist', status=status.HTTP_400_BAD_REQUEST)


class ClientUserViewSet(ModelViewSet):
    renderer_classes = (JSONRenderer, PlainTextRenderer,)
    queryset = ClientUser.objects.all().order_by('-id')
    serializer_class = ClientUserSerializer
    authentication_classes = (TokenAuthentication, JSONWebTokenAuthentication)
    permission_classes = (IsAuthenticated,)
    lookup_field = 'user_id'
    # Redefine regex in order to get user_id as id
    lookup_value_regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    @get_user_context
    def create(self, *args, **kwargs):
        request = args[0]
        client = kwargs['client']
        reseller = kwargs['reseller']

        if 'user_id' in request.data and ClientUser.objects.filter(user_id=request.data['user_id'],
                                                                   client=kwargs['client']):
            return Response("Such user already exists", status=status.HTTP_400_BAD_REQUEST)

        if 'email' in request.data and ClientUser.objects.filter(email=request.data['email'],
                                                                 client=kwargs['client']):
            return Response("User with email {} already exists".format(request.data['email']),
                            status=status.HTTP_400_BAD_REQUEST)

        if 'usage' in request.data:
            return Response("Usage should not be specified", status=status.HTTP_400_BAD_REQUEST)

        # Check if client has free space for new user or storage is unlimited
        space = free_space(client)
        if space >= request.data['storage']['limit'] or space is UNLIMITED:
            request.data['client'] = client
            request.data['application_id'] = reseller.application.id
            if 'admin' not in request.data:
                request.data['admin'] = False
            if 'superadmin' not in request.data:
                request.data['superadmin'] = False
            if 'password' in request.data:
                request.data.pop('password')
            if 'profile_type' in request.data:
                if not request.data['profile_type']:
                    request.data['profile_type'] = ClientUser.DEFAULT_PROFILE

            return ModelViewSet.create(self, *args, **kwargs)

        return Response("Client limit is reached", status=status.HTTP_400_BAD_REQUEST)

    @get_user_context
    def destroy(self, *args, **kwargs):
        client_user = get_object_or_404(ClientUser, user_id=kwargs['user_id'],
                                        client=kwargs['client'])
        client_user.delete()
        return Response("User has been deleted", status=status.HTTP_204_NO_CONTENT)

    @get_user_context
    def list(self, *args, **kwargs):
        queryset = ClientUser.objects.filter(client=kwargs['client'], superadmin=False)
        serializer = ClientUserSerializer(queryset, many=True)
        return Response(serializer.data)

    @get_user_context
    def retrieve(self, *args, **kwargs):
        queryset = ClientUser.objects.filter(client=kwargs['client'], user_id=kwargs['user_id'])
        if not queryset:
            return Response("User does not exist", status=status.HTTP_404_NOT_FOUND)
        serializer = ClientUserSerializer(queryset, many=True)
        return Response(serializer.data[0])

    @get_user_context
    def update(self, *args, **kwargs):
        client_user = ClientUser.objects.filter(client=kwargs['client'],
                                                user_id=kwargs['user_id']).first()

        if not client_user:
            args[0].data['user_id'] = kwargs['user_id']
            return self.create(*args, **kwargs)

        request = args[0]

        if 'password' in request.data:
            user = get_object_or_404(get_user_model(),
                                     username=get_app_username(kwargs['application'],
                                                               kwargs['user_id']))
            user.set_password(request.data['password'])
            user.save()
            client_user.password = request.data['password']

        if 'storage' in request.data:
            limit = request.data['storage'].get('limit')
            usage = request.data['storage'].get('usage')

            if limit is not None:
                client_user.limit = limit
            if usage is not None:
                client_user.usage = usage

            space = free_space(kwargs['client'])
            if space < client_user.limit or client_user.usage > client_user.limit:
                return Response("Storage limit is reached", HTTP_400_BAD_REQUEST)

        if 'admin' in request.data:
            client_user.admin = request.data['admin']

        if 'profile_type' in request.data:
            client_user.profile_type = request.data['profile_type']

        client_user.save()

        queryset = [client_user, ]
        serializer = ClientUserSerializer(queryset, many=True)

        return Response(serializer.data[0], status=status.HTTP_200_OK)

    @detail_route(methods=['get'])
    def token(self, request, **kwargs):
        application = Application.objects.filter(owner=request.user).first()
        if application:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               application=application).first()
        else:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               owner=request.user).first()
            if not reseller:
                admin = ClientUser.objects.filter(owner=request.user, admin=True).first()
                if not admin:
                    return Response("Client does not exist", status=HTTP_404_NOT_FOUND)
                reseller = admin.client.reseller

        client = Client.objects.filter(reseller=reseller, name=kwargs['client_name'])
        clientuser = ClientUser.objects.filter(client=client, user_id=kwargs['user_id']).first()
        if not clientuser or not clientuser.owner:
            return Response("User does not exist", status=status.HTTP_404_NOT_FOUND)

        user = clientuser.owner

        token = get_jwt_token(user)
        return Response(token, status=status.HTTP_200_OK)

    @detail_route(methods=['get'])
    def link(self, request, **kwargs):
        application = Application.objects.filter(owner=request.user).first()
        if application:
            application_id = application.id
        else:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               owner=request.user).first()
            if not reseller:
                admin = ClientUser.objects.filter(owner=request.user, admin=True).first()
                if not admin:
                    return Response("Could not determine application", status=HTTP_404_NOT_FOUND)
                reseller = admin.client.reseller

            application_id = reseller.application.id

        query = {'manual': True}

        try:
            resp = self.token(request, **kwargs)
            if resp.status_code == status.HTTP_200_OK:
                query = {'token': resp.data}
        except Exception as e:
            logger.error(e)

        login_link = urlparse.urlunparse(urlparse.urlparse('')._replace(
            scheme='http',
            netloc='.'.join([application_id, settings.SPA_HOST]),
            path='#/auth',
            query=urlencode(query)))

        return Response(login_link, status=status.HTTP_200_OK)


class UsersViewSet(ModelViewSet):
    queryset = ClientUser.objects.all()
    serializer_class = UserAuthorizationSerializer
    authentication_classes = (TokenAuthentication, JSONWebTokenAuthentication,
                              EmailBasicAuthentication)

    def list(self, request, *args, **kwargs):
        queryset = ClientUser.objects.filter(owner_id=request.user.id).first()
        serializer = UserAuthorizationSerializer(queryset)
        return Response(serializer.data)
