from . import views
from django.urls import path, include

urlpatterns = [
    path('login/', views.SignIn.as_view()),
    path('levels/', views.CurrentLevels.as_view()),
    path('classes/', views.TopicsData.as_view()),
    path('quiz/', views.QuizQuestionsData.as_view()),
    path('quizCorrection/', views.QuizCorrection.as_view()),
    path('report/', views.ReportDetails.as_view()),
    path('data/', views.data().as_view()),
    path('resetPassword/', views.ResetPassword.as_view()),

    path('addQuestion/', views.AddQuestion.as_view()),
    path('getQuestion/', views.GetQuestion.as_view()),
    path('editQuestion/', views.EditQuestion.as_view()),
    path('getAllQuestions/', views.getAllQuestions.as_view()),

    path('addBatch/', views.AddBatch.as_view()),
    path('getAllBatches/', views.GetAllBatches.as_view()),
    # path('getBatch/', views.GetBatch.as_view()),
    # path('editBatch/', views.EditBatchDetails.as_view()),
    # path('deleteBatch/', views.DeleteBatch.as_view()),

    path('addTeacher/', views.AddTeacher.as_view()),
    path('getTeachers/', views.GetTeachers.as_view()),
    # # path('assignBatch/', views.AssignBatch.as_view()),

    path('addStudent/', views.AddStudent.as_view()),
    path('getTopicsData/', views.GetTopicsData.as_view()),

    path('getTeacherBatches/', views.GetTeacherBatches.as_view()),
    path('updateBatchLink/', views.UpdateBatchLink.as_view())

    # path('getStudents/', views.GetStudents.as_view()),
    # path('assignStudentToBatch/', views.AssignStudentToBatch.as_view()),

    # path('/token', views.GetCSRFToken.as_view() , name='authentication')
]
