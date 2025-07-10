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
from .services.game_session import (
    replay_all_events, _handle_half_inning_rollover,
    get_lineup
    )
from games.services.baserunning_service import BaserunningService
from games.services.defense_service import DefenseService
from .services.atbat_service import AtBatService
from .services.game_session import get_lineup

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

    # ——— POST branch #1: Defense OR Baserunner moves ———
    if (
        request.method == "POST"
        and any(k.startswith("base_") or k.startswith("defense_") for k in request.POST)
        and "result" not in request.POST
        and "award_rbi" not in request.POST
    ):
        # 1) Pull out defense actions, e.g. {3:"PO", 5:"E"}
        defense_actions = {
            int(name.split("_", 1)[1]): value
            for name, value in request.POST.items()
            if name.startswith("defense_")
        }

        # 2) Pull out baserunner actions, e.g. {1:"ADV",2:"SB"}
        base_actions = {
            int(name.split("_", 1)[1]): value
            for name, value in request.POST.items()
            if name.startswith("base_")
        }

        # 3) Apply defense first (this may increment outs & record PO/A/E deltas)
        DefenseService(sess, get_lineup).apply(defense_actions)

        # 4) Apply baserunning—this now returns True if an out occurred
        out_occurred = BaserunningService(sess, get_lineup).apply(base_actions)

        # 5) Only roll the half-inning if there was at least one out
        if out_occurred:
            _handle_half_inning_rollover(sess, get_lineup)

        sess.save()

        # 6) Re-render the updated partial
        return render(
            request,
            "games/live_game_partial.html",
            _build_live_context(sess, get_lineup),
        )

    # 2) Branch #2: at-bat result POST
    if request.method == "POST" and "result" in request.POST:
        # collect the three base_<n> radios into a dict
        base_actions = {
            i: request.POST.get(f"base_{i}")
            for i in (1, 2, 3)
        }
        svc = AtBatService(sess, request.POST["result"], base_actions)
        svc.apply()

        return render(
            request,
            "games/live_game_partial.html",
            _build_live_context(sess, get_lineup),
        )

    # 3) Branch #3: manual RBI override
    if request.method == "POST" and "award_rbi" in request.POST:
        award = int(request.POST["award_rbi"])
        last_event = sess.events.order_by("-timestamp").first()
        if last_event:
            from stats.models import StatDelta
            StatDelta.objects.create(
                event=last_event,
                player=last_event.batter,
                stat_field="rbi",
                delta=award,
            )
        return render(
            request,
            "games/live_game_partial.html",
            _build_live_context(sess, get_lineup),
        )

    # 4) GET (or any other) → full page load
    return render(
        request,
        "games/live_game.html",
        _build_live_context(sess, get_lineup),
    )

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