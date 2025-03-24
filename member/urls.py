from django.urls import path
from .views import SignupView, LoginView, LogoutView, UserInfoView, UserEditView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('info/', UserInfoView.as_view(), name='user-info'),
    path('info/edit/', UserEditView.as_view(), name='user-edit'),
]