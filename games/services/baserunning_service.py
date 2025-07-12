"""
* Handles every runner action—ADV, ADV2, ADV3, SCORE, OUT, REMOVE, SB, CS.
* Updates the GameSession fields runner_on_first/second/third and collects which runners scored.
"""

# games/services/baserunning_service.py

from games.models import SessionInningScore, AtBatResult, StatDelta
from games.models import StatDelta

class BaserunningService:
    def __init__(self, sess, get_lineup_fn):
        self.sess       = sess
        self.get_lineup = get_lineup_fn
        self.scored     = []

    def apply(self, base_actions: dict[int,str]) -> bool:
        out_occurred = False

        for i, action in base_actions.items():
            if not action:
                continue

            runner_attr = f"runner_on_{['first','second','third'][i-1]}"
            runner = getattr(self.sess, runner_attr)
            if not runner:
                continue

            before_outs = self.sess.outs
            self.apply_runner_action(i, action, runner)
            if self.sess.outs > before_outs:
                out_occurred = True

        # persist session changes
        self.sess.save()

        return out_occurred

    def apply_runner_action(self, i: int, action: str, runner):
        base_names = ['first', 'second', 'third']
        runner_attr = f"runner_on_{base_names[i-1]}"

        # helper to get or create the SessionInningScore
        def get_sis():
            return SessionInningScore.objects.get_or_create(
                session=self.sess,
                team   = (self.sess.game.away_team if self.sess.is_top else self.sess.game.home_team),
                inning = self.sess.inning,
                is_top = self.sess.is_top,
            )[0]

        sis = None

        # — Remove runner with no stat —
        if action == 'REMOVE':
            setattr(self.sess, runner_attr, None)
            return

        # — Runner scores —
        if action == 'SCORE':
            setattr(self.sess, runner_attr, None)
            sis = get_sis()
            sis.runs += 1
            sis.save()
            self.scored.append(runner)
            return

        # — Advance 1/2/3 —
        if action in ('ADV', 'ADV2', 'ADV3'):
            delta = {'ADV':1,'ADV2':2,'ADV3':3}[action]
            tgt = i + delta
            setattr(self.sess, runner_attr, None)
            if 1 <= tgt <= 3:
                dest_attr = f"runner_on_{base_names[tgt-1]}"
                setattr(self.sess, dest_attr, runner)
            else:
                # scored on over-advance
                sis = get_sis()
                sis.runs += 1
                sis.save()
                self.scored.append(runner)
            return

        # — Out on the bases —
        if action == 'OUT':
            setattr(self.sess, runner_attr, None)
            self.sess.outs += 1
            return

        # — Stolen base —
        if action == 'SB':
            # move runner one base
            tgt = i + 1
            setattr(self.sess, runner_attr, None)
            if tgt <= 3:
                dest_attr = f"runner_on_{base_names[tgt-1]}"
                setattr(self.sess, dest_attr, runner)
            return

        # — Caught stealing —
        if action == 'CS':
            setattr(self.sess, runner_attr, None)
            self.sess.outs += 1
            return
