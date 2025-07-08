from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.db import transaction
from django.conf import settings
from types import SimpleNamespace
from .models import (
    GameSession, AtBatResult, SessionInningScore,
    StatDelta,
    )
from stats.models import LineupEntry
from players.models import PlayerPositionRating, Players
from teams.models import Lineup, TeamLineupEntry
from .forms import GameSetupForm
from stats.forms import LineupEntryForm
from .services import replay_all_events, _handle_half_inning_rollover

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

@transaction.atomic
def undo_last_event(request, session_id):
    sess = get_object_or_404(GameSession, id=session_id)
    last = sess.events.order_by('-timestamp').first()
    if last:
        last.delete()
        replay_all_events(session_id)
    return redirect('games:live_game', session_id=session_id)

def live_game(request, session_id):
    sess = get_object_or_404(GameSession, id=session_id)
    # Determine which team is currently in the field
    defending_team = sess.game.home_team if sess.is_top else sess.game.away_team

    def get_lineup(session, is_top):
        team = session.game.away_team if is_top else session.game.home_team
        return [
            e.player
            for e in LineupEntry.objects
                .filter(game=session.game, team=team)
                .order_by('batting_order')
        ]

    # ——— POST branch #1: Defense OR Baserunner moves ———
    if request.method == "POST" and 'result' in request.POST:
        code = request.POST['result']

        # 1) Who’s up?
        if sess.is_top:
            idx, pitcher = sess.away_batter_idx, sess.home_pitcher
            batting_team = sess.game.away_team
        else:
            idx, pitcher = sess.home_batter_idx, sess.away_pitcher
            batting_team = sess.game.home_team

        lineup = get_lineup(sess, sess.is_top)
        batter = lineup[idx]

        # 2) Snapshot original baserunners
        orig = {
            'first':  sess.runner_on_first,
            'second': sess.runner_on_second,
            'third':  sess.runner_on_third,
        }

        # 3) Inning score & pre-run count
        sis, _    = SessionInningScore.objects.get_or_create(
            session = sess,
            team    = batting_team,
            inning  = sess.inning,
            is_top  = sess.is_top,
        )
        pre_runs   = sis.runs
        scored     = []  # collect runners we score via radios or SF

        # 4) Handle REMOVE & SCORE radios *and* record runs
        for i, base in enumerate(('first','second','third'), start=1):
            action = request.POST.get(f'base_{i}')
            runner = orig[base]
            if action == 'REMOVE' and runner:
                setattr(sess, f'runner_on_{base}', None)
                orig[base] = None

            elif action == 'SCORE' and runner:
                sis.runs += 1
                setattr(sess, f'runner_on_{base}', None)
                scored.append(runner)
                orig[base] = None

        sis.save()
        sess.save()

        # 5) Hits / Errors / SF / SH / HR
        if code in ('1B','2B','3B'):
            sis.hits += 1
        elif code == 'E':
            sis.errors += 1
        elif code == 'SF' and orig['third']:
            sis.runs += 1
            scored.append(orig['third'])
        elif code == 'SH':
            pass
        elif code == 'HR':
            sis.hits += 1

            # everyone on base scores
            for r in orig.values():
                if r:
                    scored.append(r)
                    sis.runs += 1

            # batter scores, too
            scored.append(batter)
            sis.runs += 1

            # clear the bases
            orig = {'first': None, 'second': None, 'third': None}

        # immediately persist both hits and runs
        sis.save()
        sess.save()

        # 6) Forced‐advance (1B, BB, HBP, E, FC)
        if code in ('1B','BB','HBP','E','FC'):
            f, s, t = orig['first'], orig['second'], orig['third']
            if f and s and t:
                sis.runs += 1; scored.append(f)
                sess.runner_on_third  = s
                sess.runner_on_second = f
            elif f and s:
                sess.runner_on_third  = s
                sess.runner_on_second = f
            elif f:
                sess.runner_on_second = f
        elif code == '2B' and orig['first']:
            sess.runner_on_third = orig['first']
        elif code == '3B':
            for r in orig.values():
                if r:
                    sis.runs += 1; scored.append(r)
        elif code in ('PB','WP','BK','KPB','KWP'):
            for base in ('first','second','third'):
                r = orig[base]
                if not r: continue
                setattr(sess, f'runner_on_{base}', None)
                if base == 'third':
                    sis.runs += 1; scored.append(r)
                else:
                    dest = 'second' if base=='first' else 'third'
                    setattr(sess, f'runner_on_{dest}', r)

        sis.save()
        sess.save()

        # 7) Batter placement & automatic outs for SH/SF/FC
        if code == 'SH':
            sess.outs += 1
        elif code == 'SF':
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
            sess.runner_on_third  = batter
            sess.runner_on_first = sess.runner_on_second = None
        elif code == 'HR':
            sess.runner_on_first = sess.runner_on_second = sess.runner_on_third = None

        sess.save()

        # 8) Create the AtBatResult
        event = AtBatResult.objects.create(
            session = sess,
            batter  = batter,
            pitcher = pitcher,
            result  = code,
            inning  = sess.inning,
            is_top  = sess.is_top,
        )

        # score via the scored list, including that HR batter run
        for runner in scored:
            deltas.append(StatDelta(
                event      = event,
                player     = runner,
                stat_field = 'r',
                delta      = 1,
            ))

        # 9) Build StatDelta list
        deltas = []

        # – AB
        if code not in ('BB','HBP','IBB','SF','SH'):
            deltas.append(StatDelta(event=event, player=batter, stat_field='ab', delta=1))

        # – Hits
        if code in ('1B','2B','3B','HR'):
            deltas.append(StatDelta(event=event, player=batter, stat_field='h',  delta=1))
        if code == '2B':
            deltas.append(StatDelta(event=event, player=batter, stat_field='doubles', delta=1))
        if code == '3B':
            deltas.append(StatDelta(event=event, player=batter, stat_field='triples', delta=1))
        if code == 'HR':
            deltas.append(StatDelta(event=event, player=batter, stat_field='hr', delta=1))

        # – Walks & HBP
        if code == 'BB':
            deltas.append(StatDelta(event=event, player=batter, stat_field='bb', delta=1))
        elif code == 'HBP':
            deltas.append(StatDelta(event=event, player=batter, stat_field='hbp', delta=1))

        # – SO & DP
        if code == 'K':
            deltas.append(StatDelta(event=event, player=batter, stat_field='so', delta=1))
        if code == 'DP':
            deltas.append(StatDelta(event=event, player=batter, stat_field='dp', delta=1))

        # – Automatic RBIs on hits/SF
        auto_rbi_codes = {'1B','2B','3B','HR','SF'}
        runs_driven     = sis.runs - pre_runs
        if code in auto_rbi_codes and runs_driven > 0:
            deltas.append(StatDelta(
                event      = event,
                player     = batter,
                stat_field = 'rbi',
                delta      = runs_driven,
            ))

        # – Record runs scored (`r`) for each collected runner
        for runner in scored:
            deltas.append(StatDelta(
                event      = event,
                player     = runner,
                stat_field = 'r',
                delta      = 1,
            ))

        # 10) Bulk save all
        StatDelta.objects.bulk_create(deltas)

        # 11) Outs from K/OUT/DP/TP
        if code in ('K','OUT'):
            sess.outs += 1
        elif code == 'DP':
            sess.outs += 2
        elif code == 'TP':
            sess.outs += 3

        # 12) Process any leftover base_<n> radios
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
                # you could record additional runs here if needed
            elif action in ('ADV','ADV2','ADV3'):
                # your existing advance logic…
                pass
            elif action == 'OUT':
                setattr(sess, f'runner_on_{base}', None)
                sess.outs += 1

        sis.save()

        # 13) Advance batter & half-inning rollover
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

        # 14) RBI override prompt logic
        runs_driven = sis.runs - pre_runs
        auto_rbi_codes = {'1B','2B','3B','HR','SF'}
        needs_override = runs_driven > 0 and code not in auto_rbi_codes

        # 15) Render updated partial
        context = _build_live_context(sess, get_lineup)
        context.update({
            'runs_driven': runs_driven,
            'needs_rbi_override': needs_override,
        })
        return render(request, 'games/live_game_partial.html', context)

    # ——— POST branch #2: At-bat results ———
    if request.method == "POST" and 'result' in request.POST:
        code = request.POST['result']

        # 1) Who’s up?
        if sess.is_top:
            idx, pitcher = sess.away_batter_idx, sess.home_pitcher
            batting_team = sess.game.away_team
        else:
            idx, pitcher = sess.home_batter_idx, sess.away_pitcher
            batting_team = sess.game.home_team

        lineup = get_lineup(sess, sess.is_top)
        batter = lineup[idx]

        # 2) Snapshot baserunners
        orig = {
            'first':  sess.runner_on_first,
            'second': sess.runner_on_second,
            'third':  sess.runner_on_third,
        }

        # 3) Inning score & pre-run count
        sis, _  = SessionInningScore.objects.get_or_create(
            session = sess,
            team    = batting_team,
            inning  = sess.inning,
            is_top  = sess.is_top,
        )
        pre_runs = sis.runs
        scored   = []   # will collect each runner who scores

        # 4) Process REMOVE & SCORE radios
        for i, base in enumerate(('first','second','third'), start=1):
            action = request.POST.get(f'base_{i}')
            runner = orig[base]
            if action == 'REMOVE' and runner:
                setattr(sess, f'runner_on_{base}', None)
                orig[base] = None

            elif action == 'SCORE' and runner:
                setattr(sess, f'runner_on_{base}', None)
                scored.append(runner)
                orig[base] = None

        sis.save()
        sess.save()

        # 5) Hits / Errors / SF / SH / HR
        if code in ('1B','2B','3B'):
            sis.hits += 1
        elif code == 'E':
            sis.errors += 1
        elif code == 'SF' and orig['third']:
            scored.append(orig['third'])
        elif code == 'SH':
            pass
        elif code == 'HR':
            # everyone on base scores
            for r in orig.values():
                if r:
                    scored.append(r)
            # — and the batter scores on the HR —
            scored.append(batter)
            # clear the bases
            orig = {'first':None,'second':None,'third':None}

        sis.save()
        sess.save()

        # 6) Forced-advance (1B, BB, HBP, E, FC)
        #    [your existing forced-advance logic here…]
        sis.save()
        sess.save()

        # 7) Batter placement & auto-outs (SH/SF/FC)
        #    [your existing placement logic here…]
        sess.save()

        # 8) Create the AtBatResult record
        event = AtBatResult.objects.create(
            session = sess,
            batter  = batter,
            pitcher = pitcher,
            result  = code,
            inning  = sess.inning,
            is_top  = sess.is_top,
        )

        # 9) Build and save run totals + StatDeltas
        deltas = []

        # 9a) Create a run-scored delta for each scored runner
        for runner in scored:
            deltas.append(StartDelta(
                event           = event,
                player          = runner,
                stat_field      = 'r',
                delta           = 1,
            ))

        sis.save()  # <— Persist run increments to the scoreboard

        # 9b) Calculate and record automatic RBIs
        runs_driven     = sis.runs - pre_runs
        auto_rbi_codes  = {'1B','2B','3B','HR','SF'}
        if code in auto_rbi_codes and runs_driven > 0:
            deltas.append(StatDelta(
                event      = event,
                player     = batter,
                stat_field = 'rbi',
                delta      = runs_driven,
            ))

        # 9c) Record the rest of your usual deltas
        # – AB
        if code not in ('BB','HBP','IBB','SF','SH'):
            deltas.append(StatDelta(event=event, player=batter, stat_field='ab', delta=1))
        # – Hits
        if code in ('1B','2B','3B','HR'):
            deltas.append(StatDelta(event=event, player=batter, stat_field='h', delta=1))
        if code == '2B':
            deltas.append(StatDelta(event=event, player=batter, stat_field='doubles', delta=1))
        if code == '3B':
            deltas.append(StatDelta(event=event, player=batter, stat_field='triples', delta=1))
        if code == 'HR':
            deltas.append(StatDelta(event=event, player=batter, stat_field='hr', delta=1))
        # – Walks & HBP
        if code == 'BB':
            deltas.append(StatDelta(event=event, player=batter, stat_field='bb', delta=1))
        elif code == 'HBP':
            deltas.append(StatDelta(event=event, player=batter, stat_field='hbp', delta=1))
        # – SO & DP
        if code == 'K':
            deltas.append(StatDelta(event=event, player=batter, stat_field='so', delta=1))
        if code == 'DP':
            deltas.append(StatDelta(event=event, player=batter, stat_field='dp', delta=1))

        # 10) Bulk-create all StatDeltas
        StatDelta.objects.bulk_create(deltas)

        # 11) Handle any leftover base_<n> radios and outs
        #    [your existing code here…]

        sess.save()

        # 12) Advance batter & handle half-inning rollover
        #    [your existing code here…]

        sess.save()

        # 13) RBI override prompt logic
        #    [your existing code here…]

        return render(request, 'games/live_game_partial.html', _build_live_context(sess, get_lineup))

    # ——— POST branch #3: manual RBI override ———
    if request.method == "POST" and 'award_rbi' in request.POST:
        award = int(request.POST['award_rbi'])
        # find last plate appearance
        last_event = sess.events.order_by('-timestamp').first()
        if last_event:
            StatDelta.objects.create(
                event     = last_event,
                player    = last_event.batter,
                stat_field= 'rbi',
                delta     = award
            )

        # re-render the partial with updated stats
        context = _build_live_context(sess, get_lineup)
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
    play_choices    = AtBatResult._meta.get_field('result').choices
    defense_choices = [('A','Assist'),('PO','Put Out'),('E','Error')]

    # 6) Player stats so far
    qs = StatDelta.objects.filter(event__session=sess)

    stats = {}
    for sd in qs.values('player_id', 'stat_field').annotate(total=Sum('delta')):
        pid = sd['player_id']
        stats.setdefault(pid, {})[sd['stat_field']] = sd['total']

    player_stats = []
    for pid, sdict in stats.items():
        player = Players.objects.get(pk=pid)
        player_stats.append(SimpleNamespace(player=player, **sdict))

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

def game_stats(request, session_id):
    # 0) Fetch session and teams
    sess      = get_object_or_404(GameSession, id=session_id)
    away_team = sess.game.away_team
    home_team = sess.game.home_team

    # 1) Pull all stat-deltas for this game session
    qs = StatDelta.objects.filter(event__session=sess)

    # 2) Define desired display order, then intersect with what's present
    desired_order = [
        'ab','h','2B','3B','HR','R','RBI',
        'BB','SO','HBP','PO','A','E',
    ]
    present = set(qs.values_list('stat_field', flat=True).distinct())
    fields  = [f for f in desired_order if f in present] \
            + sorted(present - set(desired_order))

    # 3) Build human-readable headers (uppercase)
    labels = [f.upper() for f in fields]

    # 4) Aggregate deltas per (player_id, stat_field)
    stats_map = {}
    for row in qs.values('player_id','stat_field').annotate(total=Sum('delta')):
        stats_map.setdefault(row['player_id'], {})[row['stat_field']] = row['total']

    # 5) Turn that into a list of rows: { player, team, values: [...] }
    player_stats = []
    for pid, sdict in stats_map.items():
        player = Players.objects.get(pk=pid)

        # figure out home vs away
        try:
            entry = LineupEntry.objects.get(game=sess.game, player=player)
            team = entry.team
        except LineupEntry.DoesNotExist:
            if player == sess.away_pitcher:
                team = away_team
            elif player == sess.home_pitcher:
                team = home_team
            else:
                team = None

        # collect each stat in the order of `fields`
        values = [sdict.get(f, 0) for f in fields]
        player_stats.append({
            'player': player,
            'team':   team,
            'values': values,
        })

    # 6) Split into away/home and sort alphabetically
    away_stats = sorted(
        [r for r in player_stats if r['team'] == away_team],
        key=lambda r: r['player'].last_name
    )
    home_stats = sorted(
        [r for r in player_stats if r['team'] == home_team],
        key=lambda r: r['player'].last_name
    )

    # 7) Render, passing only simple lists
    return render(request, 'games/game_stats.html', {
        'session':    sess,
        'labels':     labels,     # e.g. ['AB','H','2B',…,'E']
        'away_stats': away_stats, # list of {'player','team','values'}
        'home_stats': home_stats,
    })

def substitute(request, session_id):
    sess = get_object_or_404(GameSession, id=session_id)
    # … your substitution logic here …
    return render(request, 'games/substitute.html', {...})

def session_list(request):
    sessions = GameSession.objects.filter(status='in_progress')
    return render(request, 'games/session_list.html', {
        'sessions': sessions,
    })