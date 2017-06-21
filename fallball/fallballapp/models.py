import datetime
import random
import uuid

from django.db import models
from django.db.models import Sum
from django.conf import settings
from django.utils import timezone

UNLIMITED = -1


class Application(models.Model):
    id = models.CharField(max_length=150, primary_key=True)
    owner = models.OneToOneField(settings.AUTH_USER_MODEL)
    async = models.BooleanField(default=False)

    def __str__(self):
        return self.id


class Reseller(models.Model):
    name = models.CharField(max_length=120)
    rid = models.CharField("Reseller ID", max_length=120)
    application = models.ForeignKey(Application)
    limit = models.IntegerField()
    # owner property is a foreign key related to User instance
    # It is needed to use token authorization
    owner = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta:
        unique_together = (('application', 'name'), ('application', 'rid'))

    def __str__(self):
        return self.name

    def get_clients_amount(self):
        """
        Calculate clients amount for particular reseller
        """
        return Client.objects.filter(reseller=self).count()

    def get_usage(self):
        """
        Calculate usage of all clients for particular reseller
        """
        total = (Client.objects.filter(reseller=self)
                 .annotate(sum_usage=Sum('clientuser__usage'))
                 .aggregate(Sum('sum_usage')))['sum_usage__sum']
        return total or 0


class Client(models.Model):
    ASYNC_PROVISION_DELAY = 120  # time to complete provisioning in async scenario
    STATUS_PROVISIONING = 'provisioning'
    STATUS_READY = 'ready'
    # Instance_id contains company name and used as client id
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, null=True, default=None)
    postal_code = models.CharField(max_length=16, blank=True, null=True, default=None)
    is_integrated = models.BooleanField(default=False)
    creation_date = models.DateTimeField(auto_now_add=True)
    environment = models.CharField(max_length=64, blank=True, null=True, default=None)
    country = models.CharField(max_length=64, blank=True, null=True, default=None)
    limit = models.IntegerField()
    ready_at = models.DateTimeField(default=timezone.now)

    # Every client belongs to particular reseller
    reseller = models.ForeignKey(Reseller)

    class Meta:
        unique_together = ('reseller', 'name')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.id and self.reseller.application.async:
            delay = Client.ASYNC_PROVISION_DELAY \
                    + random.randint(-Client.ASYNC_PROVISION_DELAY/2,
                                     Client.ASYNC_PROVISION_DELAY/2)
            self.ready_at = timezone.now() + datetime.timedelta(seconds=delay)
        super(Client, self).save(*args, **kwargs)

    def get_usage(self):
        """
        Calculate total usage of all client users
        """
        total = ClientUser.objects.filter(client=self).aggregate(Sum('usage'))
        return total['usage__sum'] or 0

    def get_users_amount(self):
        """
        Calculate users amount for particular company
        """
        return ClientUser.objects.filter(client=self, superadmin=False).count()

    def get_users_by_type(self):
        """
        Calculate number of users of each type for company
        """
        types = ClientUser.objects.order_by().values_list('profile_type', flat=True).distinct()
        return {k: ClientUser.objects.filter(client=self,
                                             profile_type=k,
                                             superadmin=False).count() for k in types}

    @property
    def status(self):
        return Client.STATUS_READY if timezone.now() > self.ready_at else Client.STATUS_PROVISIONING


class ClientUser(models.Model):
    DEFAULT_PROFILE = 'default'
    user_id = models.UUIDField(null=True)
    email = models.EmailField()
    owner = models.OneToOneField(settings.AUTH_USER_MODEL)
    password = models.CharField(max_length=128, blank=True)
    usage = models.IntegerField(blank=True)
    superadmin = models.BooleanField(default=False)
    admin = models.BooleanField(default=False)
    limit = models.IntegerField()
    client = models.ForeignKey(Client)
    profile_type = models.CharField(max_length=128, default=DEFAULT_PROFILE)

    class Meta:
        unique_together = (('client', 'email'), ('client', 'user_id'))

    def save(self, *args, **kwargs):
        if not self.pk and not self.user_id:
            self.user_id = kwargs.get('user_id', uuid.uuid4())
        if self.superadmin:
            self.admin = True
            self.limit = self.usage = 0
        super(ClientUser, self).save(*args, **kwargs)

    def __str__(self):
        return self.email
