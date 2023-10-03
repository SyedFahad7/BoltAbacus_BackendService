from . import views
from django.urls import path, include

urlpatterns = [
    path('login/', views.SignIn.as_view()),
    path('levels/', views.CurrentLevels.as_view())
    # path('/token', views.GetCSRFToken.as_view() , name='authentication')
]
