from os.path import join, dirname, abspath

from setuptools import find_packages, setup

with open(join(dirname(abspath(__file__)), 'requirements.txt'), 'r') as requirements:
    requirements_list = []
    for package in requirements:
        requirements_list.append(package)

setup(
    name='fallball',
    version='1.1.4',
    author='APS Connect team',
    author_email='aps@odin.com',
    packages=find_packages('fallball'),
    package_dir={'': 'fallball'},
    include_package_data=True,
    install_requires=requirements_list,
    test_suite="fallball.runtests",
    url='https://fallball.io',
    license='Apache License',
    description='Fallball file sharing service available by REST api.',
    long_description=open(join(dirname(abspath(__file__)), 'README.md')).read(),
)
