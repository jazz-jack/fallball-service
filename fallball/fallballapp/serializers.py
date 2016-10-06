from random import randint

from django.contrib.auth.models import User
from rest_framework import serializers as rest_serializers
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError

from fallballapp.models import Application, Client, ClientUser, Reseller
from fallballapp.utils import get_app_username, get_jwt_token


class AuthorizationSerializer(rest_serializers.HyperlinkedModelSerializer):
    token = rest_serializers.SerializerMethodField()

    def get_token(self, obj):
        """
        As token exists inside User object, we need to get it to show it with particular reseller
        """
        token = Token.objects.filter(user=obj.owner).first()
        return token.key if token else None


class ApplicationSerializer(AuthorizationSerializer):
    entrypoint = rest_serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ('id', 'entrypoint', 'token')

    def get_entrypoint(self, obj):
        return 'https://{}.connector.fallball.io/api/v1'.format(obj.id)

    def create(self, validated_data):
        if User.objects.filter(username=validated_data['id']).exists():
            raise ValidationError('Application with such id is already created')

        user = User.objects.create(username=validated_data['id'])
        return Application.objects.create(owner=user, **validated_data)


class StorageResellerSerializer(rest_serializers.HyperlinkedModelSerializer):
    """
    Auxiliary serializer in order to make nested json: "storage": {"usage","limit"}
    """
    usage = rest_serializers.SerializerMethodField()

    class Meta:
        model = Reseller
        fields = ('usage', 'limit')

    def get_usage(self, obj):
        return obj.get_usage()


class ResellerSerializer(AuthorizationSerializer):
    storage = StorageResellerSerializer(source='*')
    clients_amount = rest_serializers.SerializerMethodField()

    class Meta:
        model = Reseller
        fields = ('name', 'token', 'clients_amount', 'storage')

    def create(self, validated_data):
        """
        This method is overwritten in order to create User object and associate it with reseller.
        This operation is needed to create token for reseller
        """
        application_id = self.initial_data['application'].id
        reseller_name = validated_data['name']
        username = '{application_id}.{reseller_name}'.format(application_id=application_id,
                                                             reseller_name=reseller_name)

        if User.objects.filter(username=username).exists():
            raise ValidationError('Reseller with such name is already created')

        user = User.objects.create(username=username)
        return Reseller.objects.create(owner=user, application=self.initial_data['application'],
                                       **validated_data)

    def get_clients_amount(self, obj):
        return obj.get_clients_amount()


class ResellerNameSerializer(rest_serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Reseller
        fields = ('name', )


class StorageClientSerializer(rest_serializers.HyperlinkedModelSerializer):
    usage = rest_serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ('usage', 'limit')

    def get_usage(self, obj):
        return obj.get_usage()


class ClientSerializer(rest_serializers.HyperlinkedModelSerializer):
    storage = StorageClientSerializer(source='*')
    users_amount = rest_serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ('name', 'creation_date', 'users_amount', 'storage')

    def create(self, validated_data):
        """
        Method is overwritten as we need to associate user with reseller
        """
        return Client.objects.create(reseller=self.initial_data['reseller'], **validated_data)

    def get_users_amount(self, obj):
        return obj.get_users_amount()


class StorageClientUserSerializer(rest_serializers.HyperlinkedModelSerializer):

    class Meta:
        model = ClientUser
        fields = ('usage', 'limit')


class ClientUserSerializer(rest_serializers.ModelSerializer):
    storage = StorageClientUserSerializer(source='*')
    admin = rest_serializers.BooleanField()

    class Meta:
        model = ClientUser
        fields = ('email', 'password', 'storage', 'admin')

    def create(self, validated_data):
        # Usage is random but not more than limit
        usage = randint(0, validated_data['limit'])
        username = get_app_username(self.initial_data['application_id'], validated_data['email'])
        user = User.objects.create_user(username=username,
                                        password=validated_data['password'])
        return ClientUser.objects.create(usage=usage, user=user,
                                         client=self.initial_data['client'], **validated_data)


class UserAuthorizationSerializer(rest_serializers.ModelSerializer):
    storage = StorageClientUserSerializer(source='*')
    admin = rest_serializers.BooleanField()
    company = rest_serializers.SerializerMethodField()
    token = rest_serializers.SerializerMethodField()

    class Meta:
        model = ClientUser
        fields = ('email', 'storage', 'admin', 'company', 'token')

    def get_company(self, obj):
        return obj.client.name

    def get_token(self, obj):
        return get_jwt_token(obj.user)
