from django.db import models
from django.core.exceptions import ValidationError
from teams.models import Teams
from players.models import Players

class Competition(models.Model):
    name          = models.CharField(max_length=100, unique=True)
    abbreviation  = models.CharField(max_length=20, blank=True)
    description   = models.TextField(blank=True)
    has_structure = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    # ← the teams M2M goes through TeamEntry:
    teams         = models.ManyToManyField(
        'teams.Teams',
        through='TeamEntry',
        related_name='competitions'
    )

    def __str__(self):
        return self.name


class League(models.Model):
    competition  = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name='leagues'
    )
    name         = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=20, blank=True)
    has_divisions= models.BooleanField(default=False)

    # (optional) if you want to navigate from League → teams directly:
    teams        = models.ManyToManyField(
        'teams.Teams',
        through='TeamEntry',
        related_name='leagues'
    )

    def __str__(self):
        return f"{self.name} ({self.competition.abbreviation or self.competition.name})"


class Division(models.Model):
    league = models.ForeignKey(
        League,
        on_delete=models.CASCADE,
        related_name='divisions'
    )
    name   = models.CharField(max_length=100)
    # (optional) nav from Division → teams:
    teams  = models.ManyToManyField(
        'teams.Teams',
        through='TeamEntry',
        related_name='divisions'
    )

    def __str__(self):
        return f"{self.name} ({self.league.abbreviation or self.league.name})"


class TeamEntry(models.Model):
    """
    Join‐table linking a Team to a Competition, optionally scoped into a League and/or Division.
    """
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name='team_entries'
    )
    league      = models.ForeignKey(
        League,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='team_entries'
    )
    division    = models.ForeignKey(
        Division,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='team_entries'
    )
    team        = models.ForeignKey(
        'teams.Teams',
        on_delete=models.CASCADE,
        related_name='team_entries'
    )

    class Meta:
        # prevent exact dupes:
        unique_together = [
            ('competition', 'league', 'division', 'team'),
        ]

    def clean(self):
        # 1) league must belong to that competition
        if self.league and self.league.competition_id != self.competition_id:
            raise ValidationError("Selected league is not in this competition.")

        # 2) division must belong to that league
        if self.division and self.league_id != self.division.league_id:
            raise ValidationError("Selected division is not in that league.")

        # 3) if division chosen but league left blank, auto-fill it
        if self.division and not self.league:
            self.league = self.division.league

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Game(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    date_played = models.DateField()
    home_team = models.ForeignKey('teams.Teams', on_delete=models.CASCADE, related_name='home_games')
    away_team = models.ForeignKey('teams.Teams', on_delete=models.CASCADE, related_name='away_games')
    home_score = models.IntegerField(default=0)
    away_score = models.IntegerField(default=0)
    venue = models.CharField(max_length=100, blank=True, help_text="Stadium or ballpark")
    weather = models.CharField(max_length=100, blank=True, help_text="Wind, rain, etc.")

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('final', 'FInal')
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    def __str__(self):
        return f"{self.date_played}: {self.away_team} @ {self.home_team})"


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
    ab = models.PositiveSmallIntegerField(default=0)
    h = models.PositiveSmallIntegerField(default=0)
    doubles = models.PositiveSmallIntegerField(default=0)
    triples = models.PositiveSmallIntegerField(default=0)
    r = models.PositiveSmallIntegerField(default=0)
    rbi = models.PositiveSmallIntegerField(default=0)
    bb = models.PositiveSmallIntegerField(default=0)
    hbp = models.PositiveSmallIntegerField(default=0)
    so = models.PositiveSmallIntegerField(default=0)
    sf = models.PositiveSmallIntegerField(default=0)
    hr = models.PositiveSmallIntegerField(default=0)
    sb = models.PositiveSmallIntegerField(default=0)
    cs = models.PositiveSmallIntegerField(default=0)
    dp = models.PositiveSmallIntegerField(default=0)

    # Pitching
    threw = models.BooleanField(
        default=False,
        help_text="Did this player pitch in the game?"
    )
    ip_outs = models.IntegerField(default=0)  # innings pitched
    ra = models.IntegerField(default=0)
    er = models.PositiveSmallIntegerField(default=0)
    h_allowed = models.PositiveSmallIntegerField(default=0)
    bb_allowed = models.PositiveSmallIntegerField(default=0)
    k_thrown = models.PositiveSmallIntegerField(default=0)
    hb = models.PositiveSmallIntegerField(default=0)
    hra = models.PositiveSmallIntegerField(default=0)
    balk = models.PositiveSmallIntegerField(default=0)
    wp = models.PositiveSmallIntegerField(default=0)
    ibb = models.PositiveSmallIntegerField(default=0)

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
    pb = models.PositiveSmallIntegerField(default=0)
    sb_allowed = models.PositiveSmallIntegerField(default=0)
    runners_caught = models.PositiveSmallIntegerField(default=0)
    position = models.CharField(max_length=3)  # e.g., SS, C, RF

    def __str__(self):
        return f"{self.player} - {self.game}"

    @property
    def games_played(self):
        # count all stat‐lines for this player across *all* games
        return PlayerStatLine.objects.filter(player=self.player).count()

    @property
    def games_pitched(self):
        # count all stat‐lines where they recorded at least one out
        return PlayerStatLine.objects.filter(
            player=self.player,
            ip_outs__gt=0
        ).count()


class LineupEntry(models.Model):
    game = models.ForeignKey('Game', on_delete=models.CASCADE)
    team = models.ForeignKey('teams.Teams', on_delete=models.CASCADE)
    player = models.ForeignKey('players.Players', on_delete=models.CASCADE)  # updated
    batting_order = models.PositiveSmallIntegerField(null=True, blank=True)
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

    class Meta:
        unique_together = ('game', 'team', 'inning')

    def __str__(self):
        return f"{self.team} - Inning {self.inning}: {self.runs} runs"