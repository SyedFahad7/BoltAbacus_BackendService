from . import views
from django.urls import path, include

urlpatterns = [
    path('login/', views.SignIn.as_view()),
    path('levels/', views.CurrentLevels.as_view()),
    path('classes/', views.TopicsData.as_view()),
    path('quiz/', views.QuizQuestionsData.as_view()),
    path('quizCorrection/', views.QuizCorrection.as_view()),
    path('report/', views.ReportDetails.as_view()),
    path('data/', views.data().as_view())
    # path('/token', views.GetCSRFToken.as_view() , name='authentication')
]
