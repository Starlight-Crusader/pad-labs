from django.db import models
from django.contrib.auth.models import AbstractBaseUser


class User(AbstractBaseUser):
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    ratings = models.IntegerField(default=0)

    friends = models.ManyToManyField('self', blank=True)

    USERNAME_FIELD = 'username'

    def __str__(self):
        return self.username