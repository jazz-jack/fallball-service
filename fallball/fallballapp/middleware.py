import logging
import time


class RequestLogMiddleware(object):
    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):

        if response.content:
            logger = logging.getLogger(__name__)
            logger.info({'response_body': response.content})

        return response
