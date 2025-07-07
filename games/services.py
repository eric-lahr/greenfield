# games/services.py

from django.shortcuts import get_object_or_404
from django.db import transaction
from stats.models import LineupEntry
from .models import (
    GameSession,
    AtBatResult,
    SessionInningScore,
)


def get_lineup(session: GameSession, is_top: bool):
    """
    Fetch the batting order for the given half-inning.
    """
    team = session.game.away_team if is_top else session.game.home_team
    return [
        e.player
        for e in LineupEntry.objects
            .filter(game=session.game, team=team)
            .order_by('batting_order')
    ]


def apply_event_to_session(sess: GameSession, event: AtBatResult):
    """
    Mutate `sess` and its SessionInningScore to reflect one AtBatResult.
    """
    # 1) Snapshot original baserunners
    orig = {
        'first': sess.runner_on_first,
        'second': sess.runner_on_second,
        'third': sess.runner_on_third,
    }

    # 2) Ensure box-score row exists and capture pre-runs
    sis, _ = SessionInningScore.objects.get_or_create(
        session=sess,
        team   = sess.game.away_team if sess.is_top else sess.game.home_team,
        inning = sess.inning,
        is_top = sess.is_top,
    )
    code   = event.result
    batter = event.batter

    # 3) Record hits, errors, sac flies, and home runs
    if code in ('1B', '2B', '3B'):
        sis.hits += 1
    elif code == 'E':
        sis.errors += 1
    elif code == 'SF' and orig['third']:
        sis.runs += 1
    elif code == 'HR':
        sis.hits += 1
        sis.runs += 1 + sum(1 for r in orig.values() if r)
    # Note: SH yields no automatic run or hit
    sis.save()

    # 4) Forced-advance for 1B, BB, HBP, E, FC
    if code in ('1B', 'BB', 'HBP', 'E', 'FC'):
        f, s, t = orig['first'], orig['second'], orig['third']
        if f and s and t:
            sis.runs += 1
            sess.runner_on_third  = s
            sess.runner_on_second = f
        elif f and s:
            sess.runner_on_third  = s
            sess.runner_on_second = f
        elif f:
            sess.runner_on_second = f

    # 2-base and 3-base forces
    elif code == '2B' and orig['first']:
        sess.runner_on_third = orig['first']
    elif code == '3B':
        for r in orig.values():
            if r:
                sis.runs += 1

    # Passed balls / wild pitch / balk / KPB / KWP
    elif code in ('PB', 'WP', 'BK', 'KPB', 'KWP'):
        for base in ('first', 'second', 'third'):
            runner = orig[base]
            if not runner:
                continue
            setattr(sess, f'runner_on_{base}', None)
            if base == 'third':
                sis.runs += 1
            else:
                dest = 'second' if base == 'first' else 'third'
                setattr(sess, f'runner_on_{dest}', runner)

    sis.save()
    sess.save()

    # 5) Place batter and record outs as per play
    if code in ('1B', 'BB', 'HBP', 'E', 'IBB', 'FC'):
        sess.runner_on_first = batter
    elif code in ('2B',):
        sess.runner_on_second = batter
        sess.runner_on_first = None
    elif code in ('3B',):
        sess.runner_on_third = batter
        sess.runner_on_first = sess.runner_on_second = None
    elif code == 'SH' or code == 'SF':
        sess.outs += 1
    elif code == 'HR':
        sess.runner_on_first = sess.runner_on_second = sess.runner_on_third = None

    # 6) Record outs from K, OUT, DP, TP, and FC/SH/SF
    if code in ('K', 'OUT', 'SH', 'SF', 'FC'):
        sess.outs += 1
    elif code == 'DP':
        sess.outs += 2
    elif code == 'TP':
        sess.outs += 3

    sis.save()
    sess.save()

    # 7) Advance batter index & handle half-inning rollover
    lineup = get_lineup(sess, sess.is_top)
    idx = sess.away_batter_idx if sess.is_top else sess.home_batter_idx
    next_idx = (idx + 1) % len(lineup)

    if sess.outs >= 3:
        # end of half-inning
        sess.runner_on_first = sess.runner_on_second = sess.runner_on_third = None
        sess.outs = 0
        if sess.is_top:
            sess.is_top = False
            sess.away_batter_idx = next_idx
        else:
            sess.is_top = True
            sess.home_batter_idx = next_idx
            sess.inning += 1
    else:
        if sess.is_top:
            sess.away_batter_idx = next_idx
        else:
            sess.home_batter_idx = next_idx

    sess.save()


@transaction.atomic
def replay_all_events(session_id: int):
    """
    Resets GameSession and SessionInningScore, then replays every AtBatResult in order.
    """
    sess = get_object_or_404(GameSession, id=session_id)

    # Reset session state
    sess.inning = 1
    sess.is_top = True
    sess.outs = 0
    sess.away_batter_idx = 0
    sess.home_batter_idx = 0
    sess.runner_on_first = sess.runner_on_second = sess.runner_on_third = None
    sess.save()

    # Clear inning scores
    SessionInningScore.objects.filter(session=sess).delete()

    # Replay each remaining event
    for event in sess.events.order_by('timestamp'):
        apply_event_to_session(sess, event)
