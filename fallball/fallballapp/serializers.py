from random import randint
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers as rest_serializers
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError

from fallballapp.error_codes import ACTIVATION_ERROR, VALIDATION_ERROR
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
        fields = ('id', 'entrypoint', 'token', 'async')

    def get_entrypoint(self, obj):
        return 'https://{}/v1/'.format(settings.SERVICE_HOST)

    def create(self, validated_data):
        if get_user_model().objects.filter(username=validated_data['id']).exists():
            raise ValidationError('Application with such id is already created')

        user = get_user_model().objects.create(username=validated_data['id'])
        return Application.objects.create(owner=user, **validated_data)


class ApplicationPutSerializer(AuthorizationSerializer):

    class Meta:
        model = Application
        fields = ('async',)


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
        fields = ('name', 'rid', 'token', 'clients_amount', 'storage')

    def create(self, validated_data):
        """
        This method is overwritten in order to create User object and associate it with reseller.
        This operation is needed to create token for reseller
        """
        application_id = self.initial_data['application'].id
        reseller_name = validated_data['name']
        username = '{application_id}.{reseller_name}'.format(application_id=application_id,
                                                             reseller_name=reseller_name)

        if get_user_model().objects.filter(username=username).exists():
            raise ValidationError('Reseller with such name is already created')

        user = get_user_model().objects.create(username=username)
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
    users_by_type = rest_serializers.SerializerMethodField()
    email = rest_serializers.EmailField(required=False)
    postal_code = rest_serializers.CharField(required=False)

    class Meta:
        model = Client
        fields = (
            'name', 'email', 'postal_code', 'creation_date', 'users_amount', 'users_by_type',
            'storage', 'is_integrated', 'status', 'country', 'environment',)
        read_only_fields = ('status',)

    def validate_postal_code(self, value):
        if not value.isdigit() or len(value) != 5:
            # ValidationError is triggered with error code and message
            raise rest_serializers.ValidationError({
                'code': VALIDATION_ERROR,
                'message': "Postal code must be a 5-digit number",
            })

        if value.startswith('999'):
            raise rest_serializers.ValidationError({
                'code': ACTIVATION_ERROR,
                'message': "Postal code can't start with 999",
            })

        return value

    def create(self, validated_data):
        """
        Method is overwritten as we need to associate user with reseller
        """
        return Client.objects.create(reseller=self.initial_data['reseller'], **validated_data)

    def update(self, instance, validated_data):
        if 'country' in validated_data:
            del validated_data['country']
        if 'environment' in validated_data:
            del validated_data['environment']
        return super(self.__class__, self).update(instance, validated_data)

    def get_users_amount(self, obj):
        return obj.get_users_amount()

    def get_users_by_type(self, obj):
        return obj.get_users_by_type()


class StorageClientUserSerializer(rest_serializers.HyperlinkedModelSerializer):

    class Meta:
        model = ClientUser
        fields = ('usage', 'limit')


class ClientUserSerializer(rest_serializers.ModelSerializer):
    storage = StorageClientUserSerializer(source='*')
    admin = rest_serializers.BooleanField()
    superadmin = rest_serializers.BooleanField()
    password = rest_serializers.CharField(required=False)
    profile_type = rest_serializers.CharField(required=False)
    email = rest_serializers.EmailField(required=True)

    class Meta:
        model = ClientUser
        fields = ('user_id', 'email', 'password', 'storage', 'admin', 'superadmin', 'profile_type')

    def create(self, validated_data):
        # Usage is random but not more than limit
        if 'usage' not in validated_data:
            validated_data['usage'] = randint(0, validated_data['limit'])

        if 'user_id' not in validated_data:
            validated_data['user_id'] = uuid.uuid4()
        username = get_app_username(self.initial_data['application_id'], validated_data['user_id'])
        user = get_user_model().objects.create_user(username=username)

        return ClientUser.objects.create(owner=user,
                                         client=self.initial_data['client'], **validated_data)


class UserAuthorizationSerializer(rest_serializers.ModelSerializer):
    storage = StorageClientUserSerializer(source='*')
    admin = rest_serializers.BooleanField()
    company = rest_serializers.SerializerMethodField()
    token = rest_serializers.SerializerMethodField()

    class Meta:
        model = ClientUser
        fields = ('user_id', 'email', 'password', 'storage', 'admin', 'company', 'token')

    def get_company(self, obj):
        return obj.client.name

    def get_token(self, obj):
        return get_jwt_token(obj.owner)
