from django.db import models
from teams.models import Teams
from players.models import Players

class Competition(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class League(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='leagues')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.competition.name})"


class Division(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='divisions')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.league.name})"


class Game(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    date_played = models.DateField()
    home_team = models.ForeignKey('teams.Teams', on_delete=models.CASCADE, related_name='home_games')
    away_team = models.ForeignKey('teams.Teams', on_delete=models.CASCADE, related_name='away_games')
    home_score = models.PositiveSmallIntegerField()
    away_score = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.away_team} @ {self.home_team} ({self.date_played})"


class TeamStanding(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    team = models.ForeignKey('teams.Teams', on_delete=models.CASCADE)
    division = models.ForeignKey(Division, on_delete=models.SET_NULL, null=True, blank=True)
    
    wins = models.PositiveSmallIntegerField(default=0)
    losses = models.PositiveSmallIntegerField(default=0)
    ties = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('competition', 'team')

    def __str__(self):
        return f"{self.team} ({self.competition})"


class PlayerStatLine(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    player = models.ForeignKey('players.Players', on_delete=models.CASCADE)
    team = models.ForeignKey('teams.Teams', on_delete=models.CASCADE)

    # Offense
    pa = models.PositiveSmallIntegerField(default=0)
    ab = models.PositiveSmallIntegerField(default=0)
    h = models.PositiveSmallIntegerField(default=0)
    r = models.PositiveSmallIntegerField(default=0)
    rbi = models.PositiveSmallIntegerField(default=0)
    bb = models.PositiveSmallIntegerField(default=0)
    k = models.PositiveSmallIntegerField(default=0)
    hr = models.PositiveSmallIntegerField(default=0)
    sb = models.PositiveSmallIntegerField(default=0)
    cs = models.PositiveSmallIntegerField(default=0)

    # Pitching
    ip = models.FloatField(default=0)  # innings pitched
    er = models.PositiveSmallIntegerField(default=0)
    h_allowed = models.PositiveSmallIntegerField(default=0)
    bb_allowed = models.PositiveSmallIntegerField(default=0)
    k_thrown = models.PositiveSmallIntegerField(default=0)
    decision = models.CharField(
        max_length=1,
        choices=[('W', 'Win'), ('L', 'Loss'), ('S', 'Save'), ('', 'None')],
        blank=True,
        default=''
    )

    # Fielding
    po = models.PositiveSmallIntegerField(default=0)
    a = models.PositiveSmallIntegerField(default=0)
    e = models.PositiveSmallIntegerField(default=0)
    position = models.CharField(max_length=3)  # e.g., SS, C, RF

    def __str__(self):
        return f"{self.player} - {self.game}"


class LineupEntry(models.Model):
    game = models.ForeignKey('Game', on_delete=models.CASCADE)
    team = models.ForeignKey('teams.Teams', on_delete=models.CASCADE)
    player = models.ForeignKey('players.Players', on_delete=models.CASCADE)  # updated
    batting_order = models.PositiveSmallIntegerField()
    fielding_position = models.CharField(max_length=3)
    is_starting = models.BooleanField(default=True)

    class Meta:
        unique_together = ('game', 'team', 'batting_order', 'is_starting')


class Substitution(models.Model):
    game = models.ForeignKey('Game', on_delete=models.CASCADE)
    team = models.ForeignKey('teams.Teams', on_delete=models.CASCADE)
    player_in = models.ForeignKey('players.Players', on_delete=models.CASCADE, related_name='subs_in')
    player_out = models.ForeignKey('players.Players', on_delete=models.CASCADE, related_name='subs_out')
    inning = models.PositiveSmallIntegerField()
    position = models.CharField(max_length=3)  # position of player_in


class InningScore(models.Model):
    game = models.ForeignKey('Game', on_delete=models.CASCADE)
    team = models.ForeignKey('teams.Teams', on_delete=models.CASCADE)
    inning = models.PositiveSmallIntegerField()
    runs = models.PositiveSmallIntegerField()