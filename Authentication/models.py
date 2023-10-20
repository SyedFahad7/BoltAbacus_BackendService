from django.db import models


# from django.contrib.auth.models import AbstractBaseUser


class UserDetails(models.Model):
    userId = models.AutoField(primary_key=True)
    firstName = models.CharField(max_length=50)
    lastName = models.CharField(max_length=50)
    phoneNumber = models.CharField(max_length=10)
    email = models.EmailField(unique=True)
    role = models.CharField()
    encryptedPassword = models.CharField()
    created_date = models.DateField()
    blocked = models.BooleanField()


class TopicDetails(models.Model):
    levelId = models.IntegerField()
    classId = models.IntegerField()
    topicId = models.IntegerField()


class Curriculum(models.Model):
    quizId = models.IntegerField(primary_key=True)
    levelId = models.IntegerField()
    classId = models.IntegerField()
    topicId = models.IntegerField()
    quizType = models.CharField(max_length=50)
    quizName = models.CharField(max_length=50)


class QuizQuestions(models.Model):
    questionId = models.IntegerField(primary_key=True)
    quiz = models.ForeignKey(Curriculum, null=True, on_delete=models.CASCADE)
    question = models.CharField()
    correctAnswer = models.CharField()


class Progress(models.Model):
    quiz = models.ForeignKey(Curriculum, null=True, on_delete=models.CASCADE)
    user = models.ForeignKey(UserDetails, null=True, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    time = models.IntegerField()
    quizPass = models.BooleanField(default=False)
    percentage = models.FloatField(default=0)


class Batch(models.Model):
    batchId = models.IntegerField(primary_key=True)
    timeDay = models.CharField()
    timeSchedule = models.CharField()
    numberOfStudents = models.IntegerField()
    active = models.BooleanField()
    batchName = models.CharField()
    latestLevelId = models.IntegerField()
    latestClass = models.OneToOneField(Curriculum, null=True, on_delete=models.CASCADE)
    latestLink = models.CharField()


class Student(models.Model):
    user = models.OneToOneField(UserDetails, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.DO_NOTHING)


class Teacher(models.Model):
    user = models.OneToOneField(UserDetails, on_delete=models.CASCADE)
    batch = models.ManyToManyField(Batch)
# Create your models here.
