from fallball.settings import *


class DisableMigrations(object):
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return "notmigrations"


MIGRATION_MODULES = DisableMigrations()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'fallball',
        'USER': 'root',
        'PORT': '3306',
        'PASSWORD': '',
        'HOST': 'fbdb',
        'OPTIONS': {
            'init_command': 'SET character_set_server="utf8", collation_server="utf8_unicode_ci"',
        },
        'TEST': {
            'NAME': 'fallball_test'
        }
    }
}
