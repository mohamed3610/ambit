from django.conf import settings
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Widget(models.Model):
    name = models.CharField(max_length=50)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
