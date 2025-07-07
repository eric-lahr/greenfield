from django.db import models
from stadiums.models import Stadiums
from players.models import Players

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

# list all the defensive slots + DH
POSITION_CHOICES = [
    ('P','P'), ('C','C'),
    ('1B','1B'), ('2B','2B'), ('3B','3B'), ('SS','SS'),
    ('LF','LF'), ('CF','CF'), ('RF','RF'),
    ('DH','DH'),
]

class Lineup(models.Model):
    team        = models.ForeignKey('teams.Teams', on_delete=models.CASCADE, related_name='lineups')
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    allow_dh    = models.BooleanField(
        default=False,
        help_text="Check to use a 9-player (DH) lineup; leave unchecked for an 8-player non-DH lineup."
    )

    class Meta:
        unique_together = ('team','name')
        ordering = ['team','name']

    def __str__(self):
        return f"{self.team} – {self.name}"

class TeamLineupEntry(models.Model):
    lineup         = models.ForeignKey(Lineup, on_delete=models.CASCADE, related_name='entries')
    player         = models.ForeignKey(Players, on_delete=models.CASCADE)
    batting_order  = models.PositiveSmallIntegerField()
    field_position = models.CharField(max_length=2, choices=POSITION_CHOICES)

    class Meta:
        unique_together = (
            ('lineup','batting_order'),
            ('lineup','field_position'),
        )
        ordering = ['batting_order']

    def __str__(self):
        return f"{self.batting_order}: {self.player} ({self.field_position})"
