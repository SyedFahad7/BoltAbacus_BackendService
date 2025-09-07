from . import views
from django.urls import path, include

urlpatterns = [
    path('login/', views.SignIn.as_view()),
    path('levels/', views.CurrentLevels.as_view()),
    path('levelsV2/', views.CurrentLevelsV2.as_view()),
    path('classes/', views.TopicsData.as_view()),
    path('classesV2/', views.ClassProgress.as_view()),
    path('quiz/', views.QuizQuestionsData.as_view()),
    path('quizCorrection/', views.QuizCorrection.as_view()),
    path('report/', views.ReportDetails.as_view()),
    path('data/', views.data().as_view()),
    path('resetPassword/', views.ResetPassword.as_view()),
    path('resetPassword/v2/', views.ResetPasswordV2.as_view()),

    path('addQuestion/', views.AddQuestion.as_view()),
    path('getQuestion/', views.GetQuestion.as_view()),
    path('editQuestion/', views.EditQuestion.as_view()),
    path('getAllQuestions/', views.GetAllQuestions.as_view()),

    path('addBatch/', views.AddBatch.as_view()),
    path('getAllBatches/', views.GetAllBatches.as_view()),
    path('getBatch/', views.GetBatch.as_view()),

    path('editBatch/', views.EditBatchDetails.as_view()),

    path('addTeacher/', views.AddTeacher.as_view()),
    path('getTeachers/', views.GetTeachers.as_view()),
    path('getTeachersV2/', views.GetTeachersV2.as_view()),

    path('addStudent/', views.AddStudent.as_view()),
    path('getTopicsData/', views.GetTopicsData.as_view()),

    path('getTeacherBatches/', views.GetTeacherBatches.as_view()),
    path('updateBatchLink/', views.UpdateBatchLink.as_view()),
    path('updateClass/', views.UpdateClass.as_view()),
    path('getClassReport/', views.GetClassReport.as_view()),
    path('getStudentProgress/', views.GetStudentProgress.as_view()),
    path('getStudentProgressStudent/', views.GetStudentProgressFromStudent.as_view()),
    path('bulkAddQuestions/', views.BulkAddQuestions.as_view()),
    path('forgotPassword/', views.ForgotPassword.as_view()),
    path('getStudents/', views.GetStudents.as_view()),
    path('getStudentsByName/', views.GetStudentByName.as_view()),
    path('getStudentByNameV2/', views.GetStudentByNameV2.as_view()),
    path('updateStudentBatch/', views.UpdateStudentBatch.as_view()),

    path('addSubAdmin/', views.AddSubAdmin.as_view()),
    path('addTag/', views.AddOrganizationTagDetails.as_view()),
    path('getAllTags/', views.GetAllOrganizationTagNames.as_view()),
    path('getTagDetails/', views.GetOrganizationTagDetails.as_view()),
    path('updateTagDetails/', views.UpdateOrganizationDetails.as_view()),
    path('getBatchTeacher/', views.GetBatchTeacher.as_view()),
    path('updateBatchTeacher/', views.UpdateBatchTeacher.as_view()),
    path('accountDeactivate/', views.AccountDeactivation.as_view()),
    path('accountActivate/', views.AccountReactivate.as_view()),
    path('accountDeletion/', views.AccountDelete.as_view()),
    path('getStudentBatchDetails/', views.GetStudentBatchDetails.as_view()),
    path('bulkAddStudents/', views.BulkAddStudents.as_view()),

    path('submitPracticeQuestions/', views.SubmitPracticeQuestions.as_view()),
    path('getStudentPracticeQuestions/', views.GetStudentPracticeQuestions.as_view()),
    path('getStudentPracticeQuestionsStudent/', views.GetStudentPracticeQuestionsStudent.as_view()),
    path('deleteStudentPracticeQuestion/', views.DeleteStudentPracticeQuestion.as_view()),
    path('deleteQuestion/', views.DeleteQuestion.as_view()),

    # PVP and Experience endpoints
    path('createPVPRoom/', views.CreatePVPRoom.as_view()),
    path('joinPVPRoom/', views.JoinPVPRoom.as_view()),
    path('getPVPRoomDetails/', views.GetPVPRoomDetails.as_view()),
    path('setPlayerReady/', views.SetPlayerReady.as_view()),
    path('startPVPGame/', views.StartPVPGame.as_view()),
    path('submitPVPGameResult/', views.SubmitPVPGameResult.as_view()),
    path('getUserExperience/', views.GetUserExperience.as_view()),
    path('getPVPGameResult/', views.GetPVPGameResult.as_view()),
    path('updatePlayerProgress/', views.UpdatePlayerProgress.as_view()),
    path('getPVPLeaderboard/', views.GetPVPLeaderboard.as_view()),

    # Streak APIs
    path('streak/', views.GetUserStreak.as_view()),
    path('streak/update/', views.UpdateUserStreak.as_view()),
    path('streak/reset/', views.ResetUserStreak.as_view()),
    
    # Weekly Stats API
    path('weeklyStats/', views.GetWeeklyStats.as_view()),
    
    # Todo List API
    path('getUserTodoList/', views.GetUserTodoList.as_view()),
    path('addPersonalGoal/', views.AddPersonalGoal.as_view()),
    path('removePersonalGoal/', views.RemovePersonalGoal.as_view()),

]
