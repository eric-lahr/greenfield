from django.db import models

class Stadiums(models.Model):

    serial = models.AutoField(primary_key=True)
    name = models.CharField(null=True, blank=True)
    city = models.CharField(null=True, blank=True)
    state = models.CharField(null=True, blank=True)
    country = models.CharField(null=True, blank=True)
    picture = models.ImageField(
        upload_to='stadiums/', height_field=None, 
        width_field=None, max_length=100, null=True, blank=True
        )
    diagram = models.ImageField(
        upload_to='stadiums/', height_field=None, 
        width_field=None, max_length=100, null=True, blank=True
        )