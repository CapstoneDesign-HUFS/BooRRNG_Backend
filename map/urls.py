from django.urls import path
from .views import TmapRouteView

urlpatterns = [
    path('route/', TmapRouteView.as_view(), name='tmap-route'),
]