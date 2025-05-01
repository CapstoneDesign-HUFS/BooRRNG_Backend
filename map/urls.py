from django.urls import path
from . import views

urlpatterns = [
    path('poles/all/', views.all_signal_poles),
    path('poles/nearby/', views.nearby_signal_poles),
    path('poles/nearest/', views.nearest_signal_status),
    path('v2x-test/', views.test_v2x_api),
]
