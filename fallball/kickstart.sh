#!/bin/bash

set -xe
export PYTHONUNBUFFERED=1

python manage.py migrate
