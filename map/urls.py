from django.urls import path
from .views import TmapRouteView, TrafficLightView

urlpatterns = [
    path('route/', TmapRouteView.as_view(), name='tmap-route'),
    path('traffic-lights/', TrafficLightView.as_view(), name='traffic-lights'),
]
