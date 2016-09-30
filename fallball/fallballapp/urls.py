from django.conf.urls import include, url
from rest_framework_nested import routers

from .views import (ApplicationViewSet, ClientUserViewSet, ClientViewSet,
                    ResellerViewSet, UsersViewSet)

router = routers.SimpleRouter()

# Route for UI authorization
router.register(r'users', UsersViewSet)

# Route for applications
router.register(r'applications', ApplicationViewSet, base_name='applications')

router.register(r'resellers', ResellerViewSet, base_name='resellers')

resellers_router = routers.NestedSimpleRouter(router, r'resellers', lookup='reseller')
resellers_router.register(r'clients', ClientViewSet, base_name='clients')

client_router = routers.NestedSimpleRouter(resellers_router, r'clients', lookup='client')
client_router.register(r'users', ClientUserViewSet, base_name='users')

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^', include(resellers_router.urls)),
    url(r'^', include(client_router.urls)),
]
