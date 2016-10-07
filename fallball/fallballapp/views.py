from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import detail_route, list_route
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN
from rest_framework.viewsets import ModelViewSet
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from fallballapp.models import Application, Client, ClientUser, Reseller
from fallballapp.serializers import (ApplicationSerializer, ClientSerializer,
                                     ClientUserSerializer, ResellerSerializer,
                                     ResellerNameSerializer, UserAuthorizationSerializer)
from fallballapp.utils import (get_app_username, get_object_or_403, get_jwt_token,
                               is_superuser, is_application)


class ApplicationViewSet(ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = ApplicationSerializer
    queryset = Application.objects.all()

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
        username = get_app_username(kwargs['name'], kwargs['application'])
        User.objects.filter(username=username).delete()
        return Response('Reseller has been deleted', status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        application = Application.objects.filter(owner=request.user).first()
        if application:
            resellers = Reseller.objects.filter(application=application)
        else:
            resellers = Reseller.objects.filter(owner=request.user)
            if not resellers:
                admin = ClientUser.objects.filter(user=request.user, admin=True).first()
                if not admin:
                    return Response("Resellers do not exist for such account",
                                    status=HTTP_404_NOT_FOUND)

                queryset = [admin.client.reseller, ]
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

    @detail_route(methods=['get'])
    def reset(self, request, *args, **kwargs):
        """
        Repair particular reseller
        """
        return Response("Method is not implemented yet", status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @list_route(methods=['get'])
    def reset_all(self, request, *args, **kwargs):
        """
        Repair all resellers
        """
        return Response("Method is not implemented yet", status=status.HTTP_405_METHOD_NOT_ALLOWED)


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
            # Check if there is a free space for new client
            free_space = reseller.limit - reseller.get_usage()
            if free_space >= request.data['storage']['limit']:
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
                admin = ClientUser.objects.filter(user=request.user, admin=True).first()
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

    @detail_route(methods=['get'])
    def reset(self, request, *args, **kwargs):
        """
        Recreate client to initial state
        """
        return Response("Method is not implemented yet", status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @list_route(methods=['get'])
    def reset_all(self, request, *args, **kwargs):
        """
        Recreate all reseller clients to initial state
        """
        return Response("Method is not implemented yet", status=status.HTTP_405_METHOD_NOT_ALLOWED)


class ClientUserViewSet(ModelViewSet):
    queryset = ClientUser.objects.all().order_by('-id')
    serializer_class = ClientUserSerializer
    authentication_classes = (TokenAuthentication, JSONWebTokenAuthentication)
    permission_classes = (IsAuthenticated,)
    lookup_field = 'email'
    # Redefine regex in order to get user email as id
    lookup_value_regex = '[^@]+@[^@]+\.[^@/]+'

    def create(self, request, *args, **kwargs):
        application = Application.objects.filter(owner=request.user).first()
        if application:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               application=application).first()
        else:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               owner=request.user).first()
            if not reseller:
                admin = ClientUser.objects.filter(user=request.user, admin=True).first()
                if not admin:
                    return Response("Client does not exist", status=HTTP_404_NOT_FOUND)
                reseller = admin.client.reseller

        client = get_object_or_404(Client, name=kwargs['client_name'], reseller=reseller)
        # Check if client has free space for new user
        free_space = client.limit - client.get_usage()
        if free_space >= request.data['storage']['limit']:
            request.data['client'] = client
            request.data['application_id'] = reseller.application.id
            if 'admin' not in request.data:
                request.data['admin'] = False

            return ModelViewSet.create(self, request, *args, **kwargs)

        return Response("Client limit is reached", status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        application = Application.objects.filter(owner=request.user).first()
        if application:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               application=application).first()
        else:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               owner=request.user).first()
            if not reseller:
                admin = ClientUser.objects.filter(user=request.user, admin=True).first()
                if not admin:
                    return Response("Client does not exist", status=HTTP_404_NOT_FOUND)
                reseller = admin.client.reseller
        client = get_object_or_404(Client, name=kwargs['client_name'], reseller=reseller)
        client_user = get_object_or_404(ClientUser, email=kwargs['email'], client=client)
        client_user.delete()
        User.objects.filter(username='{}.{}'.format(reseller.application.id,
                                                    kwargs['email'])).delete()
        return Response("User has been deleted", status=status.HTTP_204_NO_CONTENT)

    def list(self, request, **kwargs):
        application = Application.objects.filter(owner=request.user).first()
        if application:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               application=application).first()
        else:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               owner=request.user).first()
            if not reseller:
                admin = ClientUser.objects.filter(user=request.user, admin=True).first()
                if not admin:
                    return Response("Client does not exist", status=HTTP_404_NOT_FOUND)
                reseller = admin.client.reseller

        client = get_object_or_404(Client, reseller=reseller, name=kwargs['client_name'])
        queryset = ClientUser.objects.filter(client=client)
        serializer = ClientUserSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        application = Application.objects.filter(owner=request.user).first()
        if application:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               application=application).first()
        else:
            reseller = Reseller.objects.filter(name=kwargs['reseller_name'],
                                               owner=request.user).first()
            if not reseller:
                admin = ClientUser.objects.filter(user=request.user, admin=True).first()
                if not admin:
                    return Response("Client does not exist", status=HTTP_404_NOT_FOUND)
                if not admin.client.name == kwargs['client_name']:
                    return Response("Authorization failed", status=HTTP_403_FORBIDDEN)
                reseller = admin.client.reseller

        if not reseller:
            return Response("Such reseller is not found", status=status.HTTP_404_NOT_FOUND)

        client = Client.objects.filter(reseller=reseller, name=kwargs['client_name']).first()
        queryset = ClientUser.objects.filter(client=client, email=kwargs['email'])
        if not queryset:
            return Response("User does not exist", status=status.HTTP_404_NOT_FOUND)
        serializer = ClientUserSerializer(queryset, many=True)
        return Response(serializer.data[0])

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
                admin = ClientUser.objects.filter(user=request.user, admin=True).first()
                if not admin:
                    return Response("Client does not exist", status=HTTP_404_NOT_FOUND)
                reseller = admin.client.reseller

        client = Client.objects.filter(reseller=reseller, name=kwargs['client_name'])
        client_user = ClientUser.objects.filter(client=client, email=kwargs['email']).first().user
        if not client_user:
            return Response("User does not exist", status=status.HTTP_404_NOT_FOUND)

        token = get_jwt_token(client_user)
        return Response(token, status=status.HTTP_200_OK)


class UsersViewSet(ModelViewSet):
    queryset = User.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = ClientUser.objects.filter(user_id=request.user.id).first()
        serializer = UserAuthorizationSerializer(queryset)
        return Response(serializer.data)
