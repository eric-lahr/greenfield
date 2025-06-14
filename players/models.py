from django.db import models
from django.urls import reverse

class Players(models.Model):

    serial = models.AutoField(primary_key=True)
    year = models.CharField(default='career') # meant to be a year or career
    first_name = models.CharField(default='None')
    last_name = models.CharField(default='None')
    bats = models.CharField(max_length=3, default='R/L')
    throws = models.CharField(default='R/L')
    uni_num = models.IntegerField(null=True, blank=True)
    offense = models.CharField(null=True, blank=True)
    bat_prob_hit = models.IntegerField(null=True, blank=True)
    pitching = models.CharField(null=True, blank=True)
    pitch_ctl = models.IntegerField(null=True, blank=True)
    pitch_prob_hit = models.IntegerField(null=True, blank=True)
    team_serial = models.ForeignKey('teams.Teams', on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def id(self):
        return self.serial

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.year})"

class Position(models.Model):
    name = models.CharField(max_length=3, unique=True)  # e.g., 'P', 'C', '1B', etc.

    def __str__(self):
        return self.name

class PlayerPositionRating(models.Model):
    player = models.ForeignKey(Players, on_delete=models.CASCADE, related_name='position_ratings')
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    rating = models.CharField(max_length=10)
    position_order = models.PositiveIntegerField(default=0)  # New field for ordering

    class Meta:
        unique_together = ('player', 'position')
        ordering = ['position_order']  # ⚠️ This enforces order at the query level

    def __str__(self):
        return f"{self.player} - {self.position.name}: {self.rating}"


class PlayerPicture(models.Model):

    player_serial = models.ForeignKey(Players, on_delete=models.CASCADE)
    picture = models.ImageField(
        upload_to='players/', height_field=None, 
        width_field=None, max_length=100, null=True, blank=True
        )