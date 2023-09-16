import django.contrib.auth

from . import views
from django.urls import path, include

urlpatterns = [
    path('', views.SignIn.as_view()),
    # path('/token', views.GetCSRFToken.as_view() , name='authentication')
]
