from django.db import models
from django.conf import settings
from teams.models import Teams
from players.models import Players


class GameSession(models.Model):
    game              = models.ForeignKey('stats.Game', on_delete=models.CASCADE)
    inning            = models.PositiveSmallIntegerField(default=1)
    is_top            = models.BooleanField(default=True)
    outs              = models.PositiveSmallIntegerField(default=0)
    away_batter_idx   = models.PositiveSmallIntegerField(default=0)
    home_batter_idx   = models.PositiveSmallIntegerField(default=0)
    away_pitcher      = models.ForeignKey(
        Players,
        on_delete=models.PROTECT,
        related_name='+',
        null=True, blank=True,
    )
    home_pitcher      = models.ForeignKey(
        Players,
        on_delete=models.PROTECT,
        related_name='+',
        null=True, blank=True
    )
    runner_on_first   = models.ForeignKey(
        Players,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+'
    )
    runner_on_second  = models.ForeignKey(
        Players,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+'
    )
    runner_on_third   = models.ForeignKey(
        Players,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+'
    )
    status            = models.CharField(
        max_length=20,
        choices=(
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('paused', 'Paused'),
            ('completed', 'Completed'),
        ),
        default='not_started'
    )
    started           = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('game', 'status')

    def get_box_score(self):
        away = self.game.away_team
        home = self.game.home_team
        box = {}
        for team in (away, home):
            data = {inn: {'runs': 0, 'hits': 0, 'errors': 0}
                    for inn in range(1, self.inning + 1)}
            data.update(total_runs=0, total_hits=0, total_errors=0)
            box[team] = data
        return box

    def clear_base(self, index):
        slot = ('first', 'second', 'third')[index - 1]
        setattr(self, f'runner_on_{slot}', None)


class AtBatResult(models.Model):
    session   = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name='events'
    )
    batter    = models.ForeignKey(
        Players,
        on_delete=models.PROTECT,
        related_name='+'
    )
    pitcher   = models.ForeignKey(
        Players,
        on_delete=models.PROTECT,
        related_name='+'
    )
    result    = models.CharField(
        max_length=10,
        choices=(
            ('1B', 'Single'), ('2B', 'Double'), ('3B', 'Triple'), ('HR', 'Home Run'),
            ('BB', 'Walk'), ('HBP', 'HBP'), ('K', 'Strikeout'), ('OUT', 'Other Out'),
            ('DP', 'Double Play'), ('PB', 'Passed Ball'), ('WP', 'Wild Pitch'),
            ('SF', 'Sac Fly'), ('SH', 'Sacrifice Bunt'), ('BK', 'Balk'),
            ('IBB', 'Int Walk'), ('KPB', 'K + PB'), ('KWP', 'K + WP'), ('TP', 'Triple Play'),
        )
    )
    inning    = models.PositiveSmallIntegerField()
    is_top    = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        side = 'Top' if self.is_top else 'Bot'
        return f"{self.session.game}: {side} {self.inning} - {self.batter} -> {self.result}"


class StatDelta(models.Model):
    event      = models.ForeignKey(
        AtBatResult,
        on_delete=models.CASCADE,
        related_name='stat_deltas'
    )
    player     = models.ForeignKey(
        Players,
        on_delete=models.CASCADE
    )
    stat_field = models.CharField(
        max_length=20,
        choices=(
            ('ab', 'At Bats'), ('h', 'Hits'), ('r', 'Runs'), ('rbi', 'RBIs'),
            ('bb', 'Walks'), ('hbp', 'HBP'), ('so', 'Strikeouts'),
            ('sb', 'Stolen Bases'), ('cs', 'Caught Stealing'), ('dp', 'Double Plays'),
        )
    )
    delta      = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=['player', 'stat_field']),
        ]


class SessionInningScore(models.Model):
    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name='inning_scores'
    )
    team    = models.ForeignKey(
        Teams,
        on_delete=models.CASCADE
    )
    inning  = models.PositiveSmallIntegerField()
    is_top  = models.BooleanField()
    runs    = models.PositiveSmallIntegerField(default=0)
    hits    = models.PositiveSmallIntegerField(default=0)
    errors  = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('session', 'team', 'inning', 'is_top')
        ordering = ['inning', 'is_top']

    def __str__(self):
        half = 'Top' if self.is_top else 'Bot'
        return f"{self.team} {half} {self.inning}: R{self.runs}-H{self.hits}-E{self.errors}"
