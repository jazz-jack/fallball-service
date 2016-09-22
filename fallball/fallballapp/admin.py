from django.contrib import admin

from .models import Application, Client, ClientUser, Reseller
from rest_framework.authtoken.models import Token


class BaseInline(admin.TabularInline):
    extra = 0

    def has_add_permission(self, request):
        return False


class ResellerInline(BaseInline):
    model = Reseller
    extra = 0
    readonly_fields = ['name', 'limit', 'owner']

    def has_add_permission(self, request):
        return False


class ApplicationAdmin(admin.ModelAdmin):
    fields = ['id', 'owner']
    list_display = ['id', 'token']
    inlines = [ResellerInline, ]
    readonly_fields = []

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
    inlines = [ClientInline, ]
    list_display = ('name', 'application', 'get_usage', 'limit', 'token', 'get_clients_amount')

    def get_readonly_fields(self, request, reseller=None):
        if reseller:
            return self.readonly_fields + ['name', 'owner', 'application', ]
        return self.readonly_fields

    def token(self, obj):
        return Token.objects.filter(user=obj.owner).first().key


class ClientUserInline(BaseInline):
    model = ClientUser
    extra = 0
    readonly_fields = ['email', 'limit', 'user', 'password']

    def has_add_permission(self, request):
        return False


class ClientAdmin(admin.ModelAdmin):
    fields = ['name', 'limit', 'reseller']
    list_display = ['name', 'get_usage', 'users', 'limit', 'reseller']
    readonly_fields = []
    inlines = [ClientUserInline, ]

    def get_readonly_fields(self, request, client=None):
        if client:
            return self.readonly_fields + ['reseller', 'name']
        return self.readonly_fields

    def users(self, obj):
        return obj.get_users_amount()


class ClientUserAdmin(admin.ModelAdmin):
    fields = ['email', 'client', 'password', 'user', 'usage', 'limit']
    list_display = ['email', 'client', 'password', 'usage', 'limit']
    readonly_fields = []

    def get_readonly_fields(self, request, client_user=None):
        if client_user:
            return self.readonly_fields + ['email', 'client', 'password', 'user', 'limit']
        return self.readonly_fields

admin.site.register(Application, ApplicationAdmin)
admin.site.register(Reseller, ResellerAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(ClientUser, ClientUserAdmin)

admin.site.unregister(Token)
