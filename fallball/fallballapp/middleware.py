import json
import logging
import time

from django.urls import reverse

from fallballapp.utils import get_model_object, get_application_of_object


logger = logging.getLogger('info_logger')


class RequestLogMiddleware(object):
    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        app_id = None
        reseller_name = None

        if reverse('v1:resellers-list') in request.path:
            obj = get_model_object(request.user)
            app_id = get_application_of_object(obj).id

            if request.resolver_match.url_name == 'resellers-detail':
                reseller_name = request.resolver_match.kwargs['name']
            elif request.resolver_match.url_name != 'resellers-list':
                reseller_name = request.resolver_match.kwargs['reseller_name']

        log = {}
        if app_id:
            log = {'app': app_id, }
        if reseller_name:
            log['reseller'] = reseller_name
        if response.content and response['content-type'] == 'application/json':
            log['response_body'] = json.loads(response.content.decode('utf-8'))
        try:
            logger.info(json.dumps(log))
        finally:
            return response
