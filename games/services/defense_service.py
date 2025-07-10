"""
* Processes defense radios (defense_<id>), charges put-outs/errors/assists, 
  updates the inning score, and emits StatDeltas against the last PA.
"""

# games/services/defense_service.py

from games.models import AtBatResult, SessionInningScore, StatDelta

class DefenseService:
    def __init__(self, sess, get_lineup_fn):
        self.sess         = sess
        self.get_lineup   = get_lineup_fn

    def apply(self, defense_actions: dict[int,str]):
        """
        defense_actions: { lineup_entry_id: 'PO'|'A'|'E', ... }
        """
        # 1) load or create the inning score
        sis, _ = SessionInningScore.objects.get_or_create(
            session=self.sess,
            team   = (self.sess.game.away_team if self.sess.is_top else self.sess.game.home_team),
            inning = self.sess.inning,
            is_top = self.sess.is_top,
        )

        # 2) figure out the last AtBatResult for attributing these assists/POs/errors
        last_event = self.sess.events.order_by("-timestamp").first()

        # 3) apply each defensive action
        for entry_id, code in defense_actions.items():
            entry = LineupEntry.objects.get(pk=entry_id)
            player = entry.player

            if code in ("PO", "OUT"):
                self.sess.outs += 1
                stat_field = "po"
            elif code == "A":
                stat_field = "a"
            elif code == "E":
                sis.errors += 1
                stat_field = "e"
            else:
                continue

            sis.save()
            if last_event:
                StatDelta.objects.create(
                    event      = last_event,
                    player     = player,
                    stat_field = stat_field,
                    delta      = 1,
                )

        # 4) advance batter or half-inning if any outs
        if self.sess.outs >= 3:
            # use your existing helper
            from .game_session import handle_half_inning_rollover
            handle_half_inning_rollover(self.sess, self.get_lineup)
        else:
            # just advance the batter index
            lineup = self.get_lineup(self.sess, self.sess.is_top)
            next_idx = ((self.sess.away_batter_idx if self.sess.is_top else self.sess.home_batter_idx) + 1) % len(lineup)
            if self.sess.is_top:
                self.sess.away_batter_idx = next_idx
            else:
                self.sess.home_batter_idx = next_idx

            self.sess.save()
