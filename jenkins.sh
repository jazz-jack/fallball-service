#! /bin/bash
set -xe
export PYTHONUNBUFFERED=1

python3.4 -m flake8

virtualenv -p python3.4 env
. env/bin/activate

pip install -r test-requirements.txt
python setup.py flake8

deactivate
rm -rf env