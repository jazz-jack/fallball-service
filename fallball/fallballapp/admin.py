from django.contrib import admin

from .models import Application, Client, ClientUser, Reseller

fb_models = (Application, Client, Reseller, ClientUser)
admin.site.register(fb_models)
