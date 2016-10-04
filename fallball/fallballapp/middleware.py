import logging
import time


class RequestLogMiddleware(object):
    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):

        log_data = {
            'log': "I am logging it!"
        }

        logger = logging.getLogger(__name__)
        logger.info('I am logging!!!')

        return response
