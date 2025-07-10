"""
* Handles every runner action—ADV, ADV2, ADV3, SCORE, OUT, REMOVE, SB, CS.
* Updates the GameSession fields runner_on_first/second/third and collects which runners scored.
"""

# games/services/baserunning_service.py

from games.models import StatDelta

class BaserunningService:
    def __init__(self, sess, get_lineup_fn):
        """
        sess          – your GameSession
        get_lineup_fn – function to fetch batting order, used for rollover
        """
        self.sess         = sess
        self.get_lineup   = get_lineup_fn
        # will collect runners who scored
        self.scored: list = []

    def apply(self, base_actions: dict[int,str]):
        """
        base_actions: mapping base index (1,2,3) → action code
        e.g. {1:'ADV',2:'SB',3:None}
        """

        out_occurred = False

        # delegate each runner action
        for i, action in base_actions.items():
            if not action:
                continue

            runner_attr = f"runner_on_{['first','second','third'][i-1]}"
            runner = getattr(self.sess, runner_attr)
            if not runner:
                continue

            # use your existing runner logic
            if action in ('ADV','ADV2','ADV3','SCORE','OUT','SB','CS','REMOVE'):
                # capture whether this action produced an out
                before_outs = self.sess.outs
                self.apply_runner_action(i, action, runner)
                if self.sess.outs > before_outs:
                    out_occurred = True

        # persist session
        self.sess.save()

        # if any out happened, roll the half-inning
        if out_occured:
            # deferred import to avoid circular import
            from games.services.game_session import _handle_half_inning_rollover
            _handle_half_inning_rollover(self.sess, self.get_lineup)

        # RETURN whether an out occured, so the view can roll the batter if needed
        return out_occured

    def apply_runner_action(self, i, action, runner):
        """
        (existing logic for ADV, SCORE, SB, CS, REMOVE…)
        Make sure it appends to self.scored when runners score.
        """
        # … your prior code goes here …
        # e.g. for SCORE:
        if action == 'SCORE':
            setattr(self.sess, f"runner_on_{['first','second','third'][i-1]}", None)
            self.sess.outs  # unchanged
            # increment inning score…
            # self.scored.append(runner)
        # etc.
