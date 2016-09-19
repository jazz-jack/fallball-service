# FallBall
[![Build Status](https://travis-ci.org/odin-public/fallball-service.svg?branch=master)](https://travis-ci.org/odin-public/fallball-service)
[![Coverage Status](https://coveralls.io/repos/github/odin-public/fallball-service/badge.svg?branch=master)](https://coveralls.io/github/odin-public/fallball-service?branch=master)

## Overview
FallBall is the best in class file sharing service that offers cloud storage and file synchronization for small and medium businesses (SMBs) worldwide.
This dummy service helps developers to learn [APS Lite](http://aps.odin.com) technology 

## How To Deploy
1. Create application database:
    ```
    python manage.py migrate
    ```
2. Load initial data
    ```
    python manage.py loaddata initial_data
    ```
3. Admin token
    ```
    d8cc06c05a6cd5d5b6156fd2eb963a6f1fdd039c
    ```

## Run
In order to run server you need to execute the following command from the root folder of the project:

```
python manage.py runserver <host_name>:<port>
```

## Tests
To run tests simply execute the following command:

```
python manage.py test fallballapp.tests
```
