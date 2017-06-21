from django.contrib import admin

from .models import Application, Client, ClientUser, Reseller
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.admin import TokenAdmin as BaseTokenAdmin


class BaseInline(admin.TabularInline):
    extra = 0

    def has_add_permission(self, request):
        return False


class ResellerInline(BaseInline):
    model = Reseller
    extra = 0
    readonly_fields = ['name', 'rid', 'limit', 'owner']

    def has_add_permission(self, request):
        return False


class ApplicationAdmin(admin.ModelAdmin):
    fields = ['id', 'owner', 'async']
    list_display = ['id', 'token', 'async']
    inlines = [ResellerInline, ]
    readonly_fields = []
    search_fields = ['id']

    def get_readonly_fields(self, request, application=None):
        if application:
            return self.readonly_fields + ['id', 'owner']
        return self.readonly_fields

    def token(self, obj):
        return Token.objects.filter(user=obj.owner).first().key


class ClientInline(BaseInline):
    model = Client
    extra = 0
    readonly_fields = ['name', 'limit']

    def has_add_permission(self, request):
        return False


class ResellerAdmin(admin.ModelAdmin):
    readonly_fields = []
    search_fields = ['name', 'rid', 'application__id']
    inlines = [ClientInline, ]
    list_display = (
        'name', 'rid', 'application', 'get_usage', 'limit', 'token', 'get_clients_amount')

    def get_readonly_fields(self, request, reseller=None):
        if reseller:
            return self.readonly_fields + ['name', 'rid', 'owner', 'application', ]
        return self.readonly_fields

    def token(self, obj):
        return Token.objects.filter(user=obj.owner).first().key


class ClientUserInline(BaseInline):
    model = ClientUser
    extra = 0
    readonly_fields = ['user_id', 'email', 'limit', 'owner', 'password']

    def has_add_permission(self, request):
        return False


class ClientAdmin(admin.ModelAdmin):
    fields = ['name', 'email', 'postal_code', 'limit', 'reseller', 'status', 'environment',
              'country']
    list_display = ['name', 'email', 'postal_code', 'get_usage', 'users', 'limit', 'reseller',
                    'status']
    readonly_fields = ['status']
    search_fields = ['name', 'reseller__name']
    inlines = [ClientUserInline, ]

    def get_readonly_fields(self, request, client=None):
        if client:
            return self.readonly_fields + ['reseller', 'name', 'postal_code']
        return self.readonly_fields

    def users(self, obj):
        return obj.get_users_amount()


class ClientUserAdmin(admin.ModelAdmin):
    fields = ['user_id', 'email', 'client', 'password', 'owner', 'usage', 'limit', 'profile_type',
              'admin', 'superadmin', ]
    list_display = ['user_id', 'email', 'client', 'password', 'usage', 'limit', 'profile_type',
                    'admin', 'superadmin', ]
    readonly_fields = ['user_id']
    search_fields = ['user_id', 'email', 'client__name', 'password']

    def get_readonly_fields(self, request, client_user=None):
        if client_user:
            return self.readonly_fields + ['email', 'client', 'password', 'owner', 'limit']
        return self.readonly_fields


class TokenAdmin(BaseTokenAdmin):
    fields = ('key', 'user')


admin.site.register(Application, ApplicationAdmin)
admin.site.register(Reseller, ResellerAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(ClientUser, ClientUserAdmin)

admin.site.unregister(Token)
admin.site.register(Token, TokenAdmin)
