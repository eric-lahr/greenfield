from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from types import SimpleNamespace
from .models import GameSession, PlayEvent, SessionInningScore
from stats.models import LineupEntry
from players.models import PlayerPositionRating
from .forms import GameSetupForm
from stats.forms import LineupEntryForm

def setup_game(request):
    if request.method == 'POST':
        form = GameSetupForm(request.POST)
        if form.is_valid():
            game = form.save()
            session = GameSession.objects.create(game=game)
            return redirect('games:lineup_away', session_id=session.id)
    else:
        form = GameSetupForm()
    return render(request, 'games/setup_game.html', {'form': form})

def live_game(request, session_id):
    sess = get_object_or_404(GameSession, id=session_id)

    def get_lineup(session, is_top):
        team = session.game.away_team if is_top else session.game.home_team
        return [
            e.player
            for e in LineupEntry.objects
                .filter(game=session.game, team=team)
                .order_by('batting_order')
        ]

    # Build defense_spots for the template
    # fielding side is the opposite of the batting side
    defending_team = sess.game.home_team if sess.is_top else sess.game.away_team

    # pull all lineup entries for the fielding team
    fielding_entries = list(
        LineupEntry.objects
            .filter(game=sess.game, team=defending_team)
            .select_related('player')
    )

    # define the exact defensive position order you want
    pos_order = ['P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF']

    # sort them by that order (unknown positions go to the end)
    fielding_entries.sort(
        key=lambda e: pos_order.index(e.fielding_position)
                      if e.fielding_position in pos_order
                      else len(pos_order)
    )

    # build the namespace list for your template
    defense_spots = []
    for idx, entry in enumerate(fielding_entries, start=1):
        player = entry.player
        pos    = entry.fielding_position
        try:
            rating = PlayerPositionRating.objects.get(
                player=player,
                position__name=pos
            ).rating
        except PlayerPositionRating.DoesNotExist:
            rating = 'N/A'

        defense_spots.append(SimpleNamespace(
            index=idx,
            position=pos,
            player=player,
            rating=rating
        ))

    # ——— POST branch #1: Baserunner moves ———
    if request.method == "POST" \
        and any(k.startswith('base_') for k in request.POST) \
        and 'result' not in request.POST:
        # Process each base_<n> action
        for i in (1, 2, 3):
            action = request.POST.get(f'base_{i}')
            if not action:
                continue

            runner_attr = f"runner_on_{['first','second','third'][i-1]}"
            runner = getattr(sess, runner_attr)

            if action in ('ADV','ADV2','ADV3') and runner:
                delta = {'ADV':1,'ADV2':1,'ADV3':2}[action]
                tgt = i + delta
                if 1 <= tgt <= 3:
                    setattr(sess, runner_attr, None)
                    setattr(sess,
                        f"runner_on_{['first','second','third'][tgt-1]}",
                        runner
                    )
            elif action == 'SCORE' and runner:
                setattr(sess, f'runner_on_{runner_attr}', None)
                sis.runs += 1
            elif action == 'OUT' and runner:
                setattr(sess, runner_attr, None)
                sess.outs += 1
            elif action == 'SB' and runner:
                tgt = i + 1
                if tgt <= 3:
                    setattr(sess, runner_attr, None)
                    setattr(sess,
                        f"runner_on_{['first','second','third'][tgt-1]}",
                        runner
                    )
                    # TODO: record PlayEvent(result='SB')
            elif action == 'CS' and runner:
                setattr(sess, runner_attr, None)
                sess.outs += 1
                # TODO: record PlayEvent(result='CS')
            elif action == 'REMOVE' and runner:
                setattr(sess, runner_attr, None)

        sess.save()
        context = _build_live_context(sess, get_lineup, defense_spots)
        return render(request, 'games/live_game_partial.html', context)

    # ——— POST branch #2: At-bat results ———
    if request.method == "POST" and 'result' in request.POST:
        # 1) Figure out who’s up and which team is batting
        if sess.is_top:
            idx, pitcher = sess.away_batter_idx, sess.home_pitcher
            batting_team = sess.game.away_team
        else:
            idx, pitcher = sess.home_batter_idx, sess.away_pitcher
            batting_team = sess.game.home_team

        lineup = get_lineup(sess, sess.is_top)
        batter = lineup[idx]
        code   = request.POST['result']

        # 2) Snapshot original baserunners
        orig = {
            'first':  sess.runner_on_first,
            'second': sess.runner_on_second,
            'third':  sess.runner_on_third,
        }

        # 3) Load or create the box‐score row for this half‐inning
        sis, _ = SessionInningScore.objects.get_or_create(
            session = sess,
            team    = batting_team,
            inning  = sess.inning,
            is_top  = sess.is_top,
        )

        # 4) Record hits and automatic HR run
        if code in ('1B','2B','3B'):
            sis.hits += 1
        elif code == 'E':
            sis.errors += 1
        elif code == 'HR':
            runs_scored = sum(1 for r in orig.values() if r) + 1
            sis.runs += runs_scored
            sis.hits += 1
        sis.save()

        # 5) Forced‐advance logic BEFORE placing the batter
        if code in ('1B','BB','HBP','E'):           # ← remove 'FC' here
            if orig['first']:
                if orig['second'] and orig['third']:
                    # bases loaded → 3rd scores, 2→3, 1→2
                    sis.runs += 1
                    sess.runner_on_third  = orig['second']
                    sess.runner_on_second = orig['first']
                else:
                    # only 1st occupied → 1→2
                    sess.runner_on_second = orig['first']

        elif code == '2B':
            # double: force 1→3
            if orig['first']:
                sess.runner_on_third = orig['first']

        elif code == '3B':
            # triple: everyone scores
            for r in orig.values():
                if r:
                    sis.runs += 1

        # HR scored in step 4 already
        sis.save()


        # 6) Place the batter on base (and FC→out)
        if code in ('1B','BB','HBP','E'):
            sess.runner_on_first = batter

        elif code == 'FC':                         # now handled separately
            sess.runner_on_first = batter
            sess.outs += 1

        elif code == '2B':
            sess.runner_on_second = batter
            sess.runner_on_first  = None

        elif code == '3B':
            sess.runner_on_third           = batter
            sess.runner_on_first = sess.runner_on_second = None

        elif code == 'HR':
            sess.runner_on_first = sess.runner_on_second = sess.runner_on_third = None

        # 7) Record the PlayEvent
        PlayEvent.objects.create(
            session = sess,
            batter  = batter,
            pitcher = pitcher,
            result  = code,
            inning  = sess.inning,
            is_top  = sess.is_top,
        )

        psl, _ = PlayerSessionStatLine.objects.get_or_create(
            session=sess, player=batter
        )

        #  ABs: any official PA except BB, HBP
        if code not in ('BB','HBP'):
            psl.ab += 1

        # Hits
        if code in ('1B','2B','3B','HR'):
            psl.h += 1

        # Walks & HBP
        if code == 'BB':
            psl.bb += 1
        elif code == 'HBP':
            psl.hbp += 1

        # Strikeouts
        if code == 'K':
            psl.so += 1

        # DP charged?
        if code == 'DP':
            psl.dp += 1

        psl.save()

        # 8) Increment outs for K, OUT, DP, TP
        if code in ('K','OUT'):
            sess.outs += 1
        elif code == 'DP':
            sess.outs += 2
        elif code == 'TP':
            sess.outs += 3

        # 9) Handle any base_<n> radios in the same click
        for i, base in enumerate(('first','second','third'), start=1):
            action = request.POST.get(f'base_{i}')
            runner = getattr(sess, f'runner_on_{base}')
            if not action or not runner:
                continue

            if action == 'REMOVE':
                setattr(sess, f'runner_on_{base}', None)

            elif action == 'SCORE':
                setattr(sess, f'runner_on_{base}', None)
                sis.runs += 1

            elif action in ('ADV','ADV2','ADV3'):
                if action == 'ADV':
                    move = 1
                elif action == 'ADV2':
                    move = 2
                else:  # ADV3
                    move = 3

                setattr(sess, f'runner_on_{base}', None)
                target = i + (move if action=='ADV' else move)
                if target > 3:
                    sis.runs += 1
                else:
                    dest = ('first','second','third')[target-1]
                    setattr(sess, f'runner_on_{dest}', runner)

            elif action == 'OUT':
                setattr(sess, f'runner_on_{base}', None)
                sess.outs += 1

        sis.save()

        # 10) Advance batter index & handle end-of-half-inning
        next_idx = (idx + 1) % len(lineup)
        if sess.outs >= 3:
            sess.runner_on_first = sess.runner_on_second = sess.runner_on_third = None
            sess.outs = 0
            if sess.is_top:
                sess.away_batter_idx = next_idx
                sess.is_top = False
            else:
                sess.home_batter_idx = next_idx
                sess.is_top = True
                sess.inning += 1
        else:
            if sess.is_top:
                sess.away_batter_idx = next_idx
            else:
                sess.home_batter_idx = next_idx

        sess.save()

        # 11) Render updated partial
        context = _build_live_context(sess, get_lineup, defense_spots)
        return render(request, 'games/live_game_partial.html', context)

    # ——— 3) GET (or any other method) → full page load ———
    context = _build_live_context(sess, get_lineup, defense_spots)
    return render(request, 'games/live_game.html', context)

def _build_live_context(sess, get_lineup, defense_spots):
    """Assemble all variables needed by both full and partial templates."""
    # 1) Inning-by-inning box score from DB
    innings = list(range(1, sess.inning + 1))
    away_team = sess.game.away_team
    home_team = sess.game.home_team
    player_stats = PlayerSessionStatLine.objects.filter(session=sess)

    # fetch all half-innings for this session
    sis_qs = SessionInningScore.objects.filter(session=sess)

    # build a lookup {(team_id, inning, is_top): SessionInningScore}
    sis_map = {
        (sis.team_id, sis.inning, sis.is_top): sis
        for sis in sis_qs
    }

    # helper to pull a field or default 0
    def get_half(team, inn, top, field):
        key = (team.id, inn, top)
        return getattr(sis_map.get(key), field, 0)

    away_scores = [ get_half(away_team, i, True,  'runs')  for i in innings ]
    home_scores = [ get_half(home_team, i, False, 'runs')  for i in innings ]

    # totals across all half-innings
    def total(team, field):
        return sum(getattr(sis, field) for sis in sis_qs if sis.team_id == team.id)

    away_totals = {
        'runs':   total(away_team, 'runs'),
        'hits':   total(away_team, 'hits'),
        'errors': total(away_team, 'errors'),
    }
    home_totals = {
        'runs':   total(home_team, 'runs'),
        'hits':   total(home_team, 'hits'),
        'errors': total(home_team, 'errors'),
    }

    # 2) Batter/Pitcher cards
    if sess.is_top:
        idx, pitcher = sess.away_batter_idx, sess.home_pitcher
    else:
        idx, pitcher = sess.home_batter_idx, sess.away_pitcher
    lineup = get_lineup(sess, sess.is_top)
    batter = lineup[idx]

    if sess.is_top:
        away_player, home_player = batter, pitcher
        away_rating, home_rating = batter.offense, pitcher.pitching
    else:
        away_player, home_player = pitcher, batter
        away_rating, home_rating = pitcher.pitching, batter.offense

    # 3) Baserunners
    bases = [
        SimpleNamespace(index=1, name='1st Base', runner=sess.runner_on_first),
        SimpleNamespace(index=2, name='2nd Base', runner=sess.runner_on_second),
        SimpleNamespace(index=3, name='3rd Base', runner=sess.runner_on_third),
    ]
    base_actions = [
        ('ADV','Advance'),
        ('ADV2','to 2nd'),
        ('ADV3','to 3rd'),
        ('SB','Stolen Base'),
        ('CS','Caught Stealing'),
        ('SCORE','Score'),
        ('OUT','Out'),
        ('REMOVE','Remove'),
    ]

    # 4) Defense actions
    defense_choices = [('A','Assist'),('PO','Put Out'),('E','Error')]

    return {
        'session':         sess,
        'innings':         innings,
        'away_scores':     away_scores,
        'home_scores':     home_scores,
        'away_totals':     away_totals,
        'home_totals':     home_totals,

        'away_player':     away_player,
        'home_player':     home_player,
        'away_rating':     away_rating,
        'home_rating':     home_rating,
        'play_choices':    PlayEvent._meta.get_field('result').choices,

        'defense_spots':   defense_spots,
        'defense_choices': defense_choices,

        'bases':           bases,
        'base_actions':    base_actions,
    }

def lineup_entry(request, session_id, side):
    sess = get_object_or_404(GameSession, id=session_id)
    game = sess.game
    team = game.away_team if side == 'away' else game.home_team

    form = LineupEntryForm(request.POST or None, team=team)
    if request.method == 'POST' and form.is_valid():
        # 0) Determine which team we're saving for
        team = game.away_team if side == 'away' else game.home_team

        # 1) Clear out any existing entries
        LineupEntry.objects.filter(game=game, team=team).delete()

        # 2) Save the 9 batting slots
        for i in range(1, 10):
            player   = form.cleaned_data[f'player_{i}']
            position = form.cleaned_data[f'position_{i}']
            LineupEntry.objects.create(
                game=game,
                team=team,
                player=player,
                fielding_position=position,
                batting_order=i,
            )

        # 3) Record the starting pitcher
        if side == 'away':
            sess.away_pitcher = form.cleaned_data['starting_pitcher']
            sess.save()
            # Move on to the home lineup step
            return redirect('games:lineup_home', session_id=sess.id)
        else:
            sess.home_pitcher = form.cleaned_data['starting_pitcher']

            # 4) **Initialize both batter pointers** now that both lineups exist
            sess.away_batter_idx = 0
            sess.home_batter_idx = 0

            sess.save()
            # All set—time to go live
            return redirect('games:live_game', session_id=sess.id)

    # Build the form fields for display
    batting_fields = [
        (form[f'player_{i}'], form[f'position_{i}'])
        for i in range(1, 10)
    ]

    return render(request, 'games/lineup_entry.html', {
        'form':           form,
        'session':        sess,
        'team':           team,
        'side':           side,
        'batting_fields': batting_fields,
    })

def substitute(request, session_id):
    sess = get_object_or_404(GameSession, id=session_id)
    # … your substitution logic here …
    return render(request, 'games/substitute.html', {...})

from django.shortcuts import render
from .models import GameSession

def session_list(request):
    sessions = GameSession.objects.filter(status='in_progress')
    return render(request, 'games/session_list.html', {
        'sessions': sessions,
    })