from django.urls import path
from .views import (
    AllTrafficLightsView,
    NearbyTrafficLightsView,
    V2XSignalTestView,
    TmapRouteView,
    SegmentedRouteView,
    TmapSegmentedRouteView,
    SignalStatusView 
)

urlpatterns = [
    path('traffic-lights/all/', AllTrafficLightsView.as_view(), name='all-traffic-lights'),
    path('traffic-lights/nearby/', NearbyTrafficLightsView.as_view(), name='nearby-traffic-lights'),
    path('traffic-lights/v2x-test/', V2XSignalTestView.as_view(), name='v2x-signal-test'),
    path('traffic-lights/tmap-route/', TmapRouteView.as_view(), name='tmap-route'),
    path('traffic-lights/segmented-route/', SegmentedRouteView.as_view(), name='segmented-route'),
    path('traffic-lights/tmap-segmented-route/', TmapSegmentedRouteView.as_view(), name='tmap-segmented-route'),
    path('traffic-lights/signal-status/', SignalStatusView.as_view(), name='signal-status'),  # ← 이 줄 추가
]

