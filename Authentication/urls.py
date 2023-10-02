import django.contrib.auth
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView,TokenVerifyView

from . import views
from django.urls import path, include

urlpatterns = [
    path('login/', views.SignIn.as_view()),
    path('levels/', views.CurrentLevels.as_view())
    # path('/token', views.GetCSRFToken.as_view() , name='authentication')
]
