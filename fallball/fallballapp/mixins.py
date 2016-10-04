from django.utils.decorators import decorator_from_middleware

from middleware import RequestLogMiddleware


class RequestLogViewsetMixin(object):

    @classmethod
    def as_view(cls, *args, **kwargs):
        viewset = super(RequestLogViewsetMixin, cls).as_view(*args, **kwargs)
        viewset = decorator_from_middleware(RequestLogMiddleware)(viewset)
        return viewset
