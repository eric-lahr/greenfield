from django.db import models
from stadiums.models import Stadiums

class Teams(models.Model):

    serial = models.AutoField(primary_key=True)
    first_name = models.CharField(default='All Time')
    team_name = models.CharField(default='Team')
    stadium_serial = models.ForeignKey('stadiums.Stadiums', on_delete=models.CASCADE, related_name='teams', null=True, blank=True)
    common_lineup_serial = models.ForeignKey('teams.Lineups', on_delete=models.CASCADE, related_name='teams_common', null=True, blank=True)
    vs_r_lineup_serial = models.ForeignKey('teams.Lineups', on_delete=models.CASCADE, related_name='teams_vs_r', null=True, blank=True)
    vs_l_lineup_serial = models.ForeignKey('teams.Lineups', on_delete=models.CASCADE, related_name='teams_vs_l', null=True, blank=True)
    lineup3_serial = models.ForeignKey('teams.Lineups', on_delete=models.CASCADE, related_name='teams_lu3', null=True, blank=True)
    lineup4_serial = models.ForeignKey('teams.Lineups', on_delete=models.CASCADE, related_name='teams_lu4', null=True, blank=True)
    lineup5_serial = models.ForeignKey('teams.Lineups', on_delete=models.CASCADE, related_name='teams_lu5', null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.team_name}"

    @property
    def id(self):
        return self.serial

class Lineups(models.Model):

    serial = models.AutoField(primary_key=True)
    first = models.ForeignKey('players.Players', on_delete=models.CASCADE, related_name='lineups_1st')
    first_pos = models.CharField()
    second = models.ForeignKey('players.Players', on_delete=models.CASCADE, related_name='lineups_2nd')
    second_pos = models.CharField()
    third = models.ForeignKey('players.Players', on_delete=models.CASCADE, related_name='lineups_3rd')
    third_pos = models.CharField()
    fourth = models.ForeignKey('players.Players', on_delete=models.CASCADE, related_name='lineups_4th')
    fourth_pos = models.CharField()
    fifth = models.ForeignKey('players.Players', on_delete=models.CASCADE, related_name='lineups_5th')
    fifth_pos = models.CharField()
    sixth = models.ForeignKey('players.Players', on_delete=models.CASCADE, related_name='lineups_6th')
    sixth_pos = models.CharField()
    seventh = models.ForeignKey('players.Players', on_delete=models.CASCADE, related_name='lineups_7th')
    seventh_pos = models.CharField()
    eighth = models.ForeignKey('players.Players', on_delete=models.CASCADE, related_name='lineups_8th')
    eighth_pos = models.CharField()
    ninth = models.ForeignKey('players.Players', on_delete=models.CASCADE, related_name='lineups_9th', null=True, blank=True)
    ninth_pos = models.CharField()

    @property
    def id(self):
        return self.serial

class Logos(models.Model):
    team_serial = models.ForeignKey(Teams, on_delete=models.SET_NULL, null=True, blank=True)
    main_logo = models.ImageField(
        upload_to='logos/', height_field=None, 
        width_field=None, max_length=100, null=True, blank=True
        )
    hat_logo = models.ImageField(
        upload_to='logos/', height_field=None, 
        width_field=None, max_length=100, null=True, blank=True
        )