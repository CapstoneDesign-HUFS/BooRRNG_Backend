from django.urls import path
from .views import AllTrafficLightsView, NearbyTrafficLightsView, V2XSignalTestView

urlpatterns = [
    path('traffic-lights/all/', AllTrafficLightsView.as_view(), name='all-traffic-lights'),
    path('traffic-lights/nearby/', NearbyTrafficLightsView.as_view(), name='nearby-traffic-lights'),
    path('traffic-lights/v2x-test/', V2XSignalTestView.as_view()), 
]
