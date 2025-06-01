from django.db import models
from django.urls import reverse

class Players(models.Model):

    serial = models.AutoField(primary_key=True)
    year = models.CharField(default='career') # meant to be a year or career
    first_name = models.CharField(default='None')
    last_name = models.CharField(default='None')
    positions = models.CharField(default='None')
    bats = models.CharField(max_length=3, default='R/L')
    throws = models.CharField(default='R/L')
    uni_num = models.IntegerField(null=True, blank=True)
    defense = models.CharField(default='84')
    offense = models.CharField(null=True, blank=True)
    pitching = models.CharField(null=True, blank=True)
    team_serial = models.ForeignKey('teams.Teams', on_delete=models.SET_NULL, null=True, blank=True)

class PlayerPicture(models.Model):

    player_serial = models.ForeignKey(Players, on_delete=models.CASCADE)
    picture = models.ImageField(
        upload_to='players/', height_field=None, 
        width_field=None, max_length=100, null=True, blank=True
        )