from django.shortcuts import render, redirect, get_object_or_404
from types import SimpleNamespace
from .models import GameSession, PlayEvent
from stats.models import LineupEntry
from players.models import PlayerPositionRating
from games.forms import GameSetupForm
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

    # 1) Build defense_spots (always in context)
    fielding_entries = LineupEntry.objects.filter(
        game=sess.game,
        team=sess.game.away_team if sess.is_top else sess.game.home_team
    ).order_by('batting_order')

    defense_spots = []
    for idx, entry in enumerate(fielding_entries, start=1):
        player = entry.player
        pos    = entry.fielding_position
        try:
            ppr = PlayerPositionRating.objects.get(player=player, position__name=pos)
            rating = ppr.rating
        except PlayerPositionRating.DoesNotExist:
            rating = 'N/A'
        defense_spots.append(SimpleNamespace(
            index=idx,
            position=pos,
            player=player,
            rating=rating
        ))

    # ————— POST BRANCH #1: Baserunner actions —————
    if request.method == "POST" and any(k.startswith('base_') for k in request.POST):
        # move/remove runners based on base_1, base_2, base_3
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
                setattr(sess, runner_attr, None)
                # TODO: increment that team’s run in your box‐score storage

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

            elif action == 'REMOVE':
                setattr(sess, runner_attr, None)

        sess.save()

        # render updated fragment
        context = _build_live_context(sess, get_lineup, defense_spots)
        return render(request, 'games/live_game_partial.html', context)

    # ————— POST BRANCH #2: At‐bat result —————
    if request.method == "POST" and 'result' in request.POST:
        # figure out who's batting and who's pitching
        if sess.is_top:
            idx, pitcher = sess.away_batter_idx, sess.home_pitcher
        else:
            idx, pitcher = sess.home_batter_idx, sess.away_pitcher

        lineup = get_lineup(sess, sess.is_top)
        batter = lineup[idx]
        code   = request.POST['result']

        # record the play
        PlayEvent.objects.create(
            session=sess,
            batter=batter,
            pitcher=pitcher,
            result=code,
            inning=sess.inning,
            is_top=sess.is_top,
        )

        # update outs
        if code in ('K', 'OUT'):
            sess.outs += 1

        # advance batter index
        next_idx = (idx + 1) % len(lineup)
        if sess.outs >= 3:
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

        # render updated fragment
        context = _build_live_context(sess, get_lineup, defense_spots)
        return render(request, 'games/live_game_partial.html', context)

    # ————— GET: initial load —————
    context = _build_live_context(sess, get_lineup, defense_spots)
    return render(request, 'games/live_game.html', context)


def _build_live_context(sess, get_lineup, defense_spots):
    """
    Assemble the full context dict for both full and partial renders.
    """
    # 1) Scoreboard data
    box      = sess.get_box_score()
    innings  = list(range(1, sess.inning + 1))
    away, home = sess.game.away_team, sess.game.home_team
    away_scores = [box[away][i]['runs']  for i in innings]
    home_scores = [box[home][i]['runs']  for i in innings]
    away_totals = {
        'runs':   box[away]['total_runs'],
        'hits':   box[away]['total_hits'],
        'errors': box[away]['total_errors'],
    }
    home_totals = {
        'runs':   box[home]['total_runs'],
        'hits':   box[home]['total_hits'],
        'errors': box[home]['total_errors'],
    }

    # 2) Current batter/pitcher cards
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
        ('ADV','Advance'),('ADV2','to 2nd'),('ADV3','to 3rd'),
        ('SB','Stolen Base'),('CS','Caught Stealing'),
        ('SCORE','Score'),('OUT','Out'),('REMOVE','Remove'),
    ]

    # 4) Assemble everything
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
        'defense_choices': [('A','Assist'),('PO','Put Out'),('E','Error')],

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