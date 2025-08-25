from django.contrib import admin
from .models import (
    OrganizationTag, UserDetails, TopicDetails, Curriculum, QuizQuestions, 
    Progress, Batch, Student, Teacher, PracticeQuestions,
    UserExperience, PVPRoom, PVPRoomPlayer, PVPGameSession, 
    PVPPlayerAnswer, PVPGameResult, UserStreak, UserCoins, UserAchievement
)

# Register your models here.
admin.site.register(OrganizationTag)
admin.site.register(UserDetails)
admin.site.register(TopicDetails)
admin.site.register(Curriculum)
admin.site.register(QuizQuestions)
admin.site.register(Progress)
admin.site.register(Batch)
admin.site.register(Student)
admin.site.register(Teacher)
admin.site.register(PracticeQuestions)

# PVP and Experience models
admin.site.register(UserExperience)
admin.site.register(PVPRoom)
admin.site.register(PVPRoomPlayer)
admin.site.register(PVPGameSession)
admin.site.register(PVPPlayerAnswer)
admin.site.register(PVPGameResult)
admin.site.register(UserStreak)
admin.site.register(UserCoins)
admin.site.register(UserAchievement)
