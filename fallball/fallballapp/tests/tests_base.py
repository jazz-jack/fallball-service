import json

from django.contrib.auth.models import User
from django.core.management import call_command
from django.shortcuts import get_object_or_404
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from fallballapp.models import Client, ClientUser, Reseller
