"""
* Knows what each result_code (1B, 2B, HR, SF, SH, BB, HBP, K, DP, TP, etc.) means for hits, outs, batter placement.
* Calls into the stats_service to assemble the right deltas.
"""

# games/services/atbat_service.py

from django.db import transaction
from django.shortcuts import get_object_or_404
from games.models import (
    GameSession, AtBatResult, SessionInningScore, StatDelta
    )
from .game_session import get_lineup, _handle_half_inning_rollover
from .baserunning_service import BaserunningService

class AtBatService:
    def __init__(self, sess: GameSession, code: str, base_actions: dict[str,str]):
        """
        sess        – the current GameSession
        code        – e.g. '1B','BB','HR', etc.
        base_actions– mapping like {1:'ADV',2:'SCORE',3:None}
        """
        self.sess         = sess
        self.code         = code
        self.base_actions = base_actions

        # figure out who’s batting and which team
        if sess.is_top:
            self.idx, self.pitcher = sess.away_batter_idx, sess.home_pitcher
            self.batting_team = sess.game.away_team
        else:
            self.idx, self.pitcher = sess.home_batter_idx, sess.away_pitcher
            self.batting_team = sess.game.home_team

        lineup = get_lineup(sess, sess.is_top)
        self.batter = lineup[self.idx]

        # snapshot
        self.orig = {
            'first':  sess.runner_on_first,
            'second': sess.runner_on_second,
            'third':  sess.runner_on_third,
        }
        self.sis, _   = SessionInningScore.objects.get_or_create(
            session=sess,
            team=self.batting_team,
            inning=sess.inning,
            is_top=sess.is_top,
        )
        self.pre_runs = self.sis.runs

        # service to handle all base_<n> actions
        self.br = BaserunningService(sess, get_lineup)

        # will collect all StatDelta instances here
        self.deltas: list[StatDelta] = []

    @transaction.atomic
    def apply(self):
        # 1) delegate all runner actions (SCORE, ADV, SB, CS, etc.)
        for base_num, action in self.base_actions.items():
            runner = getattr(self.sess, f"runner_on_{['first','second','third'][base_num-1]}")
            if action and runner:
                self.br.apply_runner_action(base_num, action, runner)

        # 2) record hits / errors / sac flies / HR
        self._apply_hit_error_and_runs()

        # 3) forced‐advance runners on 1B, BB, HBP, E, FC
        self._apply_forced_advance()

        # 4) place batter & auto‐outs (SH, SF, FC, etc.)
        self._apply_batter_placement()

        # persist scoreboard / session changes
        self.sis.save()
        self.sess.save()

        # 5) create the AtBatResult
        event = AtBatResult.objects.create(
            session=self.sess,
            batter=self.batter,
            pitcher=self.pitcher,
            result=self.code,
            inning=self.sess.inning,
            is_top=self.sess.is_top,
        )

        # 6) build run‐scored deltas
        for runner in self.br.scored:
            self.deltas.append(StatDelta(
                event=event,
                player=runner,
                stat_field='r',
                delta=1,
            ))

        # 7) RBIs for batter if auto‐eligible
        runs_driven = self.sis.runs - self.pre_runs
        if self.code in {'1B','2B','3B','HR','SF'} and runs_driven > 0:
            self.deltas.append(StatDelta(
                event=event,
                player=self.batter,
                stat_field='rbi',
                delta=runs_driven,
            ))

        # 8) AB, H, BB, HBP, SO, DP, etc.
        self._apply_standard_deltas(event)

        # bulk‐save them
        StatDelta.objects.bulk_create(self.deltas)

        # 9) increment outs from K/OUT/DP/TP
        self._apply_outs_and_rollover()

        return event, self.deltas

    def _apply_hit_error_and_runs(self):
        c = self.code
        if c in ('1B','2B','3B'):
            self.sis.hits += 1
        elif c == 'E':
            self.sis.errors += 1
        elif c == 'SF' and self.orig['third']:
            # sac fly scores runner on third
            self.sis.runs += 1
            self.br.scored.append(self.orig['third'])
        elif c == 'HR':
            # hit and clear bases
            self.sis.hits += 1
            for r in self.orig.values():
                if r:
                    self.sis.runs += 1
                    self.br.scored.append(r)
            # batter scores, too
            self.br.scored.append(self.batter)
            self.sis.runs += 1
            self.orig = {'first':None,'second':None,'third':None}

    def _apply_forced_advance(self):
        c = self.code
        f,s,t = self.orig['first'], self.orig['second'], self.orig['third']
        if c in ('1B','BB','HBP','E','FC'):
            if f and s and t:
                self.sis.runs += 1; self.br.scored.append(f)
                self.sess.runner_on_third  = s
                self.sess.runner_on_second = f
            elif f and s:
                self.sess.runner_on_third  = s
                self.sess.runner_on_second = f
            elif f:
                self.sess.runner_on_second = f
        elif c == '2B' and f:
            self.sess.runner_on_third = f
        elif c == '3B':
            for r in self.orig.values():
                if r:
                    self.sis.runs += 1; self.br.scored.append(r)
        elif c in ('PB','WP','BK','KPB','KWP'):
            for base in ('first','second','third'):
                r = self.orig[base]
                if not r:
                    continue
                setattr(self.sess, f'runner_on_{base}', None)
                if base == 'third':
                    self.sis.runs += 1; self.br.scored.append(r)
                else:
                    dest = 'second' if base=='first' else 'third'
                    setattr(self.sess, f'runner_on_{dest}', r)

    def _apply_batter_placement(self):
        c = self.code
        if c == 'SH':
            self.sess.outs += 1
        elif c == 'SF':
            self.sess.outs += 1
        elif c in ('1B','BB','HBP','E','IBB'):
            self.sess.runner_on_first = self.batter
        elif c == 'FC':
            self.sess.runner_on_first = self.batter
            self.sess.outs += 1
        elif c == '2B':
            self.sess.runner_on_second = self.batter
            self.sess.runner_on_first  = None
        elif c == '3B':
            self.sess.runner_on_third  = self.batter
            self.sess.runner_on_first = self.sess.runner_on_second = None
        elif c == 'HR':
            # bases already cleared above
            pass

    def _apply_standard_deltas(self, event: AtBatResult):
        c = self.code
        # AB
        if c not in ('BB','HBP','IBB','SF','SH'):
            self.deltas.append(StatDelta(event=event, player=self.batter, stat_field='ab', delta=1))
        # Hits
        if c in ('1B','2B','3B','HR'):
            self.deltas.append(StatDelta(event=event, player=self.batter, stat_field='h', delta=1))
        if c == '2B':
            self.deltas.append(StatDelta(event=event, player=self.batter, stat_field='2B', delta=1))
        if c == '3B':
            self.deltas.append(StatDelta(event=event, player=self.batter, stat_field='3B', delta=1))
        if c == 'HR':
            self.deltas.append(StatDelta(event=event, player=self.batter, stat_field='HR', delta=1))
        # Walks & HBP
        if c == 'BB':
            self.deltas.append(StatDelta(event=event, player=self.batter, stat_field='BB', delta=1))
        elif c == 'HBP':
            self.deltas.append(StatDelta(event=event, player=self.batter, stat_field='HBP', delta=1))
        # SO, DP
        if c == 'K':
            self.deltas.append(StatDelta(event=event, player=self.batter, stat_field='SO', delta=1))
        if c == 'DP':
            self.deltas.append(StatDelta(event=event, player=self.batter, stat_field='DP', delta=1))

    def _apply_outs_and_rollover(self):
        c = self.code
        if c in ('K','OUT'):
            self.sess.outs += 1
        elif c == 'DP':
            self.sess.outs += 2
        elif c == 'TP':
            self.sess.outs += 3

        # now roll half-inning if needed and advance batter
        _handle_half_inning_rollover(self.sess, get_lineup)
