from django.db import models
from django.conf import settings
from collections import defaultdict
from teams.models import Teams
from players.models import Players


class GameSession(models.Model):
    game      = models.ForeignKey('stats.Game', on_delete=models.CASCADE)
    inning    = models.PositiveSmallIntegerField(default=1)
    is_top    = models.BooleanField(default=True)
    outs      = models.PositiveSmallIntegerField(default=0)
    away_batter_idx= models.PositiveSmallIntegerField(default=0)
    home_batter_idx= models.PositiveSmallIntegerField(default=0)
    away_pitcher = models.ForeignKey(
        'players.Players',
        on_delete=models.PROTECT,
        related_name='+',
        null=True, blank=True,
        )
    home_pitcher = models.ForeignKey(
        'players.Players',
        on_delete=models.PROTECT,
        related_name='+',
        null=True, blank=True
    )
    runner_on_first  = models.ForeignKey(
        'players.Players', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+'
        )
    runner_on_second = models.ForeignKey(
        'players.Players', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+'
        )
    runner_on_third  = models.ForeignKey(
        'players.Players', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+'
        )
    status    = models.CharField(max_length=20,
        choices=(
        ('not_started','Not Started'),
        ('in_progress','In Progress'),
        ('paused','Paused'),
        ('completed','Completed'),
        ), default='not_started')
    started   = models.DateTimeField(auto_now_add=True)

    def get_box_score(self):
        """
        Returns a nested dict:
          {
            TeamA: {1: {'runs':0,'hits':0,'errors':0}, 2: {...}, ..., 'total_runs':0, 'total_hits':0, 'total_errors':0},
            TeamB: { ... same structure ... }
          }
        """
        # Figure out the two sides
        away = self.game.away_team
        home = self.game.home_team

        # Prepare per‐inning slots plus totals
        box = {}
        for team in (away, home):
            data = {}
            # innings 1 through current inning
            for inn in range(1, self.inning + 1):
                data[inn] = {'runs': 0, 'hits': 0, 'errors': 0}
            # overall totals
            data['total_runs']   = 0
            data['total_hits']   = 0
            data['total_errors'] = 0
            box[team] = data

        return box

    def clear_base(self, index):
        slot = ('first','second','third')[index-1]
        setattr(self, f'runner_on_{slot}', None)

    class Meta:
        unique_together = ('game','status')


class PlayEvent(models.Model):
    session   = models.ForeignKey(GameSession,
                                  on_delete=models.CASCADE,
                                  related_name='events')
    batter    = models.ForeignKey(Players,
                                  on_delete=models.PROTECT,
                                  related_name='+')
    pitcher   = models.ForeignKey(Players,
                                  on_delete=models.PROTECT,
                                  related_name='+')
    result    = models.CharField(max_length=10,
                                 choices=(
                                   ('1B','Single'),('2B','Double'),('3B','Triple'),('HR','Home Run'),
                                   ('BB','Walk'),('HBP','HBP'),('K','Strikeout'),('OUT','Other Out'),
                                   ('DP', 'Double Play'),('PB', 'Passed Ball'),('WP', 'Wild Pitch'),
                                   ('SF', 'Sac Fly'),('SH', 'Sacrifice Bunt'),('BK', 'Balk'),
                                   ('IBB', 'Int Walk'),('KPB', 'K + PB'),('KWP', 'K + WP'),
                                   ('TP', 'Triple Play'),
                                 ))
    inning    = models.PositiveSmallIntegerField()
    is_top    = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)


class SessionInningScore(models.Model):
    session = models.ForeignKey(
        'games.GameSession',      # points at your live‐play session
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
        unique_together = ('session','team','inning','is_top')
        ordering = ['inning','is_top']

    def __str__(self):
        half = 'Top' if self.is_top else 'Bot'
        return f"{self.team} {half} {self.inning}: R{self.runs}-H{self.hits}-E{self.errors}"


class PlayerSessionStatLine(models.Model):
    session = models.ForeignKey(
        GameSession, on_delete=models.CASCADE, related_name='player_stats'
    )
    player  = models.ForeignKey(
        Players,     on_delete=models.CASCADE
    )
    # Basic batting stats
    ab  = models.PositiveSmallIntegerField(default=0)
    h   = models.PositiveSmallIntegerField(default=0)
    r   = models.PositiveSmallIntegerField(default=0)
    rbi = models.PositiveSmallIntegerField(default=0)
    bb  = models.PositiveSmallIntegerField(default=0)
    hbp = models.PositiveSmallIntegerField(default=0)
    so  = models.PositiveSmallIntegerField(default=0)
    sb  = models.PositiveSmallIntegerField(default=0)
    cs  = models.PositiveSmallIntegerField(default=0)
    dp  = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('session','player')
