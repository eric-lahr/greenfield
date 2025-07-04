from django.shortcuts import render, redirect, get_object_or_404
from .models import GameSession, PlayEvent
from stats.models import LineupEntry
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

    # ————— POST (an at‐bat) —————
    if request.method == "POST":
        # pick the correct index & pitcher before any changes
        if sess.is_top:
            idx     = sess.away_batter_idx
            pitcher = sess.home_pitcher
        else:
            idx     = sess.home_batter_idx
            pitcher = sess.away_pitcher

        lineup = get_lineup(sess, sess.is_top)
        batter = lineup[idx]
        code   = request.POST['result']

        # record the event
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

        # compute next index for this team
        next_idx = (idx + 1) % len(lineup)

        # half-inning rollover?
        if sess.outs >= 3:
            sess.outs = 0

            # advance this team’s index before switching sides
            if sess.is_top:
                sess.away_batter_idx = next_idx
                # switch to bottom, same inning
                sess.is_top = False
            else:
                sess.home_batter_idx = next_idx
                # switch to top, next inning
                sess.is_top = True
                sess.inning += 1

        else:
            # ordinary advance within the same half
            if sess.is_top:
                sess.away_batter_idx = next_idx
            else:
                sess.home_batter_idx = next_idx

        sess.save()

        # now fall through to re-render with updated state

    # 3) Build scoreboard data (box, innings, scores, totals) as before…
    box = sess.get_box_score()
    innings = list(range(1, sess.inning + 1))
    away, home = sess.game.away_team, sess.game.home_team
    away_scores = [box[away][i]['runs'] for i in innings]
    home_scores = [box[home][i]['runs'] for i in innings]
    away_totals = {
        'runs': box[away]['total_runs'],
        'hits': box[away]['total_hits'],
        'errors': box[away]['total_errors'],
    }
    home_totals = {
        'runs': box[home]['total_runs'],
        'hits': box[home]['total_hits'],
        'errors': box[home]['total_errors'],
    }

    # 4) After possible POST side‐flip, recompute who’s up
    if sess.is_top:
        idx     = sess.away_batter_idx
        pitcher = sess.home_pitcher
    else:
        idx     = sess.home_batter_idx
        pitcher = sess.away_pitcher

    lineup = get_lineup(sess, sess.is_top)
    batter = lineup[idx]

    # 5) Map away/home cards
    if sess.is_top:
        away_player, home_player = batter, pitcher
        away_rating, home_rating = batter.offense, pitcher.pitching
    else:
        away_player, home_player = pitcher, batter
        away_rating, home_rating = pitcher.pitching, batter.offense

    context = {
        'session':      sess,
        'away_player':  away_player,
        'home_player':  home_player,
        'away_rating':  away_rating,
        'home_rating':  home_rating,
        'play_choices': PlayEvent._meta.get_field('result').choices,
        'innings':      innings,
        'away_scores':  away_scores,
        'home_scores':  home_scores,
        'away_totals':  away_totals,
        'home_totals':  home_totals,
    }

    template = (
        'games/live_game_partial.html'
        if request.headers.get('HX-Request') else
        'games/live_game.html'
    )
    return render(request, template, context)

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