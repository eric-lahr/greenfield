from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from types import SimpleNamespace
from .models import (
    GameSession, PlayEvent, SessionInningScore,
    PlayerSessionStatLine,
    )
from stats.models import LineupEntry
from players.models import PlayerPositionRating, Players
from teams.models import Lineup, TeamLineupEntry
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
        pre_runs = sis.runs

        # 4) Record hits, errors, sac flies, and HR runs
        if code in ('1B','2B','3B'):
            sis.hits += 1

        elif code == 'E':
            sis.errors += 1

        elif code == 'SF':
            # sacrifice fly: score runner on third if present, +RBI
            if orig['third']:
                sis.runs += 1

        elif code == 'SH':
            # sacrifice bunt: no automatic run, scorer may advance via radio
            pass

        elif code == 'HR':
            # home run: hit + everyone on + batter
            sis.hits += 1
            runs_scored = sum(1 for r in orig.values() if r) + 1
            sis.runs += runs_scored

        sis.save()


        # 5) Forced‐advance & live‐ball specials BEFORE placing the batter

        # SINGLE‐type forces (1B, BB, HBP, E but NOT FC)
        if code in ('1B','BB','HBP','E'):
            if orig['first']:
                if orig['second'] and orig['third']:
                    # bases loaded → 3rd scores, 2→3, 1→2
                    sis.runs += 1
                    sess.runner_on_third  = orig['second']
                    sess.runner_on_second = orig['first']
                else:
                    # only 1st → 2nd
                    sess.runner_on_second = orig['first']

        # DOUBLE forces 1st → 3rd
        elif code == '2B':
            if orig['first']:
                sess.runner_on_third = orig['first']

        # TRIPLE scores everyone
        elif code == '3B':
            for r in orig.values():
                if r:
                    sis.runs += 1

        # Passed Ball / Wild Pitch / Balk & KPB/KWP: all runners advance one
        elif code in ('PB','WP','BK','KPB','KWP'):
            for b_name, runner in orig.items():
                if not runner:
                    continue
                # clear old spot
                setattr(sess, f'runner_on_{b_name}', None)
                # advance or score
                if b_name == 'third':
                    sis.runs += 1
                else:
                    dest = ['first','second','third'][['first','second','third'].index(b_name)+1]
                    setattr(sess, f'runner_on_{dest}', runner)

        sis.save()


        # 6) Place the batter on base (and record FC / KPB / KWP outs)
        if code == 'SH':
            # sacrifice bunt: batter out, no base, no AB
            sess.outs += 1

        elif code in ('SF',):
            # sac fly: batter out, no base, no AB
            sess.outs += 1

        elif code in ('1B','BB','HBP','E','IBB'):
            sess.runner_on_first = batter

        elif code == 'FC':
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
        if code not in ('BB','HBP','IBB','SF','SH'):
            psl.ab += 1

        # Hits
        if code in ('1B','2B','3B','HR'):
            psl.h += 1

        if code == '2B': psl.doubles += 1
        if code == '3B': psl.triples += 1
        if code == 'HR':psl.hr += 1

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
        runs_driven = sis.runs - pre_runs
        auto_rbi_codes = {'1B','2B','3B','HR','SF'}
        needs_override = runs_driven > 0 and code not in auto_rbi_codes

        # 11) Render updated partial
        context = _build_live_context(sess, get_lineup, defense_spots)
        context.update({
            'needs_rbi_override': needs_override,
            'runs_driven': runs_driven,
        })
        return render(request, 'games/live_game_partial.html', context)

    # ——— POST branch #3: manual RBI override ———
    if request.method == "POST" and 'award_rbi' in request.POST:
        award = int(request.POST['award_rbi'])
        # find last plate appearance
        last_event = sess.events.order_by('-timestamp').first()
        if last_event:
            psl, _ = PlayerSessionStatLine.objects.get_or_create(
                session=sess,
                player=last_event.batter
            )
            psl.rbi += award
            psl.save()

        # re-render the partial with updated stats
        context = _build_live_context(sess, get_lineup, defense_spots)
        return render(request, 'games/live_game_partial.html', context)

    # ——— 4) GET (or any other method) → full page load ———
    context = _build_live_context(sess, get_lineup)
    return render(request, 'games/live_game.html', context)

def _build_live_context(sess, get_lineup):
    """Assemble all variables needed by both full and partial templates."""

    # 1) Inning-by-inning box score
    innings   = list(range(1, sess.inning + 1))
    away_team = sess.game.away_team
    home_team = sess.game.home_team

    sis_qs = SessionInningScore.objects.filter(session=sess)
    sis_map = {
        (sis.team_id, sis.inning, sis.is_top): sis
        for sis in sis_qs
    }
    def get_half(team, inn, top, field):
        return getattr(sis_map.get((team.id, inn, top)), field, 0)

    away_scores = [get_half(away_team, i, True,  'runs')  for i in innings]
    home_scores = [get_half(home_team, i, False, 'runs')  for i in innings]

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
        ('ADV','Advance'), ('ADV2','to 2nd'), ('ADV3','to 3rd'),
        ('SB','Stolen Base'), ('CS','Caught Stealing'),
        ('SCORE','Score'), ('OUT','Out'), ('REMOVE','Remove'),
    ]

    # 4) Defensive alignment (recomputed every half-inning)
    defending_team = sess.game.home_team if sess.is_top else sess.game.away_team
    entries = LineupEntry.objects.filter(
        game=sess.game,
        team=defending_team
    ).select_related('player')

    pos_order = ['P','C','1B','2B','3B','SS','LF','CF','RF']
    sorted_entries = sorted(
        entries,
        key=lambda e: pos_order.index(e.fielding_position)
                      if e.fielding_position in pos_order
                      else len(pos_order)
    )

    defense_spots = []
    for i, entry in enumerate(sorted_entries, start=1):
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
            index=i,
            position=pos,
            player=player,
            rating=rating
        ))

    # 5) Choice lists
    play_choices    = PlayEvent._meta.get_field('result').choices
    defense_choices = [('A','Assist'),('PO','Put Out'),('E','Error')]

    # 6) Player stats so far
    player_stats = PlayerSessionStatLine.objects.filter(session=sess)

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
        'play_choices':    play_choices,
        'bases':           bases,
        'base_actions':    base_actions,
        'defense_spots':   defense_spots,
        'defense_choices': defense_choices,
        'player_stats':    player_stats,
    }

def lineup_entry(request, session_id, side):
    sess = get_object_or_404(GameSession, id=session_id)
    game = sess.game
    team = game.away_team if side=='away' else game.home_team

    # 1) Fetch all saved lineups
    all_lineups   = team.lineups.all()

    # 2) Determine which lineup to use
    chosen_id = request.GET.get('lineup_id')
    default_lineup = None
    if chosen_id:
        default_lineup = all_lineups.filter(id=chosen_id).first()
    if default_lineup is None and all_lineups.exists():
        default_lineup = all_lineups.first()

    # 3) Build initial_data from that lineup
    initial_data = {}
    if default_lineup:
        for entry in default_lineup.entries.all():
            i = entry.batting_order
            initial_data[f'player_{i}']   = entry.player.pk
            initial_data[f'position_{i}'] = entry.field_position

    # 4) Instantiate your form (POST or GET) with that initial_data
    form = LineupEntryForm(request.POST or None,
                           team=team,
                           initial=initial_data)

    if request.method=='POST' and form.is_valid():
        # Clear out old entries
        LineupEntry.objects.filter(game=game, team=team).delete()

        # Save new batting slots
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

        # Record starting pitcher and redirect on success...
        if side=='away':
            sess.away_pitcher = form.cleaned_data['starting_pitcher']
            sess.save()
            return redirect('games:lineup_home', session_id=sess.id)
        else:
            sess.home_pitcher    = form.cleaned_data['starting_pitcher']
            sess.away_batter_idx = sess.home_batter_idx = 0
            sess.save()
            return redirect('games:live_game', session_id=sess.id)

    # Build the batting_fields for rendering
    batting_fields = [
        (form[f'player_{i}'], form[f'position_{i}'])
        for i in range(1, 10)
    ]

    return render(request, 'games/lineup_entry.html', {
        'session':         sess,
        'team':            team,
        'side':            side,
        'form':            form,
        'batting_fields':  batting_fields,
        'all_lineups':     all_lineups,
        'default_lineup':  default_lineup,
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