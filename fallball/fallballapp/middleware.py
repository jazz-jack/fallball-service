import logging
import time


logger = logging.getLogger('info_logger')


class RequestLogMiddleware(object):
    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        if response.content:
            logger.info({'response_body': response.content})
        return response
