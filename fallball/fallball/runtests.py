#!/usr/bin/env python
import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner

os.environ['DJANGO_SETTINGS_MODULE'] = 'fallballapp.tests.settings'
django.setup()

TestRunner = get_runner(settings)
test_runner = TestRunner()
failures = test_runner.run_tests(['fallballapp.tests'])
sys.exit(bool(failures))
