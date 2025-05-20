from django.db import models
from django.urls import reverse

class Batters(models.Model):

    serial = models.AutoField(primary_key=True)