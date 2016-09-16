#! /bin/bash
set -xe
export PYTHONUNBUFFERED=1

python3.4 -m flake8

virtualenv -p python3.4 env
. env/bin/activate

pip install -r requirements.txt
pip install -r test-requirements.txt
mv fallball/fallball/settings_fallball.py fallball/fallball/settings.py

python setup.py flake8
python setup.py test

deactivate
rm -rf env