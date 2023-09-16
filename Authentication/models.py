from django.db import models


class User(models.Model):
    firstName = models.CharField(max_length=50)
    lastName = models.CharField(max_length=50)
    phoneNumber = models.IntegerField()
    email = models.EmailField()
    role = models.CharField()
    encryptedPassword = models.CharField()
    created_date = models.DateField()
    blocked = models.BooleanField()

# Create your models here.
