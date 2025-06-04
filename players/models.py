from django.db import models
from django.urls import reverse

class Players(models.Model):

    serial = models.AutoField(primary_key=True)
    year = models.CharField(default='career') # meant to be a year or career
    first_name = models.CharField(default='None')
    last_name = models.CharField(default='None')
    position_1 = models.CharField(default='None')
    position_2 = models.CharField(default='None')
    position_3 = models.CharField(default='None')
    position_4 = models.CharField(default='None')
    position_5 = models.CharField(default='None')
    position_6 = models.CharField(default='None')
    position_7 = models.CharField(default='None')
    position_8 = models.CharField(default='None')
    position_9 = models.CharField(default='None')
    bats = models.CharField(max_length=3, default='R/L')
    throws = models.CharField(default='R/L')
    uni_num = models.IntegerField(null=True, blank=True)
    defense_1 = models.CharField(default='84')
    defense_2 = models.CharField(default='None')
    defense_3 = models.CharField(default='None')
    defense_4 = models.CharField(default='None')
    defense_5 = models.CharField(default='None')
    defense_6 = models.CharField(default='None')
    defense_7 = models.CharField(default='None')
    defense_8 = models.CharField(default='None')
    defense_9 = models.CharField(default='None')
    offense = models.CharField(null=True, blank=True)
    bat_prob_hit = models.IntegerField(null=True, blank=True)
    pitching = models.CharField(null=True, blank=True)
    pitch_ctl = models.IntegerField(null=True, blank=True)
    pitch_prob_hit = models.IntegerField(null=True, blank=True)
    team_serial = models.ForeignKey('teams.Teams', on_delete=models.SET_NULL, null=True, blank=True)

class PlayerPicture(models.Model):

    player_serial = models.ForeignKey(Players, on_delete=models.CASCADE)
    picture = models.ImageField(
        upload_to='players/', height_field=None, 
        width_field=None, max_length=100, null=True, blank=True
        )