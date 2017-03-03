import json
import logging
import time

from django.urls import reverse

from fallballapp.utils import get_model_object, get_application_of_object


logger = logging.getLogger('info_logger')


class RequestLogMiddleware(object):

    def __init__(self):
        self.log = {'request': {'headers': {}}, 'response': {'headers': {}}}

    def process_request(self, request):
        request.start_time = time.time()

        self.log['request'] = {'headers': {}}

        if 'HTTP_AUTHORIZATION' in request.META:
            token = request.META['HTTP_AUTHORIZATION']
            self.log['request']['headers']['HTTP_AUTHORIZATION'] = token

        if request.body:
            try:
                self.log['request']['body'] = json.loads(request.body.decode())
            except ValueError:
                self.log['request']['body'] = {"message": "body is not valid json"}

    def process_response(self, request, response):
        self.log['response'] = {'headers': {}}

        if not hasattr(request, 'user'):
            return response

        app_id = None
        reseller_name = None

        if response.content and response['content-type'] == 'application/json':
            self.log['response']['body'] = json.loads(response.content.decode())

        self.log['request']['headers']['REQUEST_METHOD'] = request.META['REQUEST_METHOD'],

        if 'CONTENT_TYPE' in request.META:
            self.log['request']['headers']['CONTENT_TYPE'] = request.META['CONTENT_TYPE'],

        self.log['response']['headers'] = response._headers

        if not request.user.is_anonymous and not request.user.is_superuser:

            if reverse('v1:resellers-list') in request.path:
                obj = get_model_object(request.user)
                app_id = get_application_of_object(obj).id

                if request.resolver_match.url_name == 'resellers-detail':
                    reseller_name = request.resolver_match.kwargs['name']
                elif request.resolver_match.url_name != 'resellers-list':
                    reseller_name = request.resolver_match.kwargs['reseller_name']

            if app_id:
                self.log['response'] = {'app': app_id, }
            if reseller_name:
                self.log['reseller'] = reseller_name

        logger.info(json.dumps(self.log))

        return response
