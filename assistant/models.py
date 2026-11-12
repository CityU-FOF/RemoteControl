from django.db import models
from django.contrib.auth.models import User

class Root(models.Model):
    label = models.CharField(max_length=100)
    path = models.TextField(unique=True)
    device = models.CharField(max_length=40)
    inode = models.CharField(max_length=40)

class Control(models.Model):
    paused = models.BooleanField(default=False)
    generation = models.PositiveIntegerField(default=1)

class Device(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    revoked = models.BooleanField(default=False)
