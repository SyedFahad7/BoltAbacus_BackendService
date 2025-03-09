from django.db import models
from django.db.models.functions.datetime import datetime


# from django.contrib.auth.models import AbstractBaseUser


class OrganizationTag(models.Model):
    tagId = models.AutoField(primary_key=True)
    organizationName = models.CharField()
    tagName = models.CharField(default="BoltAbacus", unique=True)
    isIndividualTeacher = models.BooleanField(default=False)
    numberOfTeachers = models.IntegerField(default=0)
    numberOfStudents = models.IntegerField(default=0)
    expirationDate = models.DateField(default=datetime.today)
    totalNumberOfStudents = models.IntegerField(default=0)
    maxLevel = models.IntegerField(default=1)
    maxClass = models.IntegerField(default=1)


class UserDetails(models.Model):
    userId = models.AutoField(primary_key=True)
    firstName = models.CharField(max_length=50)
    lastName = models.CharField(max_length=50)
    phoneNumber = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    role = models.CharField()
    encryptedPassword = models.CharField()
    created_date = models.DateField()
    blocked = models.BooleanField()
    blockedTimestamp = models.DateField(default=datetime.today)
    tag = models.ForeignKey(OrganizationTag, to_field="tagId", null=True, on_delete=models.CASCADE, default=1)


class TopicDetails(models.Model):
    levelId = models.IntegerField()
    classId = models.IntegerField()
    topicId = models.IntegerField()


class Curriculum(models.Model):
    quizId = models.AutoField(primary_key=True)
    levelId = models.IntegerField()
    classId = models.IntegerField()
    topicId = models.IntegerField()
    quizType = models.CharField(max_length=50)
    quizName = models.CharField(max_length=50)


class QuizQuestions(models.Model):
    questionId = models.AutoField(primary_key=True)
    quiz = models.ForeignKey(Curriculum, to_field='quizId', null=True, on_delete=models.CASCADE)
    question = models.CharField()
    correctAnswer = models.CharField()


class Progress(models.Model):
    quiz = models.ForeignKey(Curriculum, to_field='quizId', null=True, on_delete=models.CASCADE)
    user = models.ForeignKey(UserDetails, to_field='userId', null=True, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    time = models.IntegerField(default=0)
    quizPass = models.BooleanField(default=False)
    percentage = models.FloatField(default=0)


class Batch(models.Model):
    batchId = models.AutoField(primary_key=True)
    timeDay = models.CharField()
    timeSchedule = models.CharField()
    numberOfStudents = models.IntegerField()
    active = models.BooleanField()
    batchName = models.CharField()
    latestLevelId = models.IntegerField()
    latestClassId = models.IntegerField()
    latestLink = models.CharField()
    tag = models.ForeignKey(OrganizationTag, to_field="tagId", null=True, on_delete=models.CASCADE, default=1)


class Student(models.Model):
    user = models.OneToOneField(UserDetails, to_field='userId', on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, to_field='batchId', on_delete=models.DO_NOTHING)
    latestLevelId = models.IntegerField(default=1)
    latestClassId = models.IntegerField(default=1)


class Teacher(models.Model):
    user = models.ForeignKey(UserDetails, to_field='userId', on_delete=models.CASCADE)
    batchId = models.IntegerField()


class PracticeQuestions(models.Model):
    practiceQuestionId = models.AutoField(primary_key=True)
    user = models.ForeignKey(UserDetails, to_field='userId', on_delete=models.CASCADE)
    practiceType = models.CharField(max_length=20)
    operation = models.CharField(max_length=50)
    numberOfDigits = models.IntegerField(default=1)
    numberOfQuestions = models.IntegerField(default=0)
    numberOfRows = models.IntegerField(default=1)
    zigZag = models.BooleanField(default=False)
    includeSubtraction = models.BooleanField(default=False)
    persistNumberOfDigits = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    totalTime = models.FloatField(default=0)
    averageTime = models.FloatField(default=0)
# Create your models here.
