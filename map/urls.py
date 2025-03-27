from django.urls import path
from .views import TmapRouteView, TrafficLightView, SignalPhaseView, PoleView, RouteRecommendationView

urlpatterns = [
    path('route/', RouteRecommendationView.as_view(), name='route-recommendation'),
    path('route/', TmapRouteView.as_view(), name='tmap-route'),
    path('traffic-lights/', TrafficLightView.as_view(), name='traffic-lights'),
    path("signal-phase/", SignalPhaseView.as_view(), name="signal-phase"),
     path("poles/", PoleView.as_view(), name="poles"),
]
