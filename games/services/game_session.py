# games/services/game_session.py

from django.shortcuts import get_object_or_404
from django.db import transaction
from games.models import SessionInningScore
from .baserunning_service import BaserunningService
from .defense_service    import DefenseService
from games.models        import GameSession, AtBatResult

"""
* Public API: apply_play(result_code, runner_actions, defense_actions) and undo_last_play().
* Loads the GameSession and current SessionInningScore, delegates to the sub-services, 
  handles half-inning rollover, and returns the new AtBatResult (or void for undo).
"""

def _handle_half_inning_rollover(sess, get_lineup):
    """
    Check sess.outs and, if >=3, roll to the next half-inning:
    clear bases, reset outs, flip is_top, bump inning if needed,
    and advance the batter index.
    """
    if sess.outs >= 3:
        # clear the bases
        sess.runner_on_first = sess.runner_on_second = sess.runner_on_third = None
        sess.outs = 0
        lineup = get_lineup(sess, sess.is_top)

        if sess.is_top:
            # we just finished the top → switch to bottom, advance away idx
            sess.is_top = False
            sess.away_batter_idx = (sess.away_batter_idx + 1) % len(lineup)
        else:
            # we just finished the bottom → new inning
            sess.is_top = True
            sess.inning += 1
            sess.home_batter_idx = (sess.home_batter_idx + 1) % len(lineup)

        sess.save()
    else:
        # just advance the batter index in this half
        lineup = get_lineup(sess, sess.is_top)
        if sess.is_top:
            sess.away_batter_idx = (sess.away_batter_idx + 1) % len(lineup)
        else:
            sess.home_batter_idx = (sess.home_batter_idx + 1) % len(lineup)
        sess.save()


def get_lineup(session: GameSession, is_top: bool):
    team = session.game.away_team if is_top else session.game.home_team
    return [
        e.player
        for e in session.game.lineupentry_set
                  .filter(team=team)
                  .order_by('batting_order')
    ]

@transaction.atomic
def replay_all_events(session_id: int):
    sess = get_object_or_404(GameSession, id=session_id)
    # reset state …
    for event in sess.events.order_by('timestamp'):
        apply_event_to_session(sess, event)
