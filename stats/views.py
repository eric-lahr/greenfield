from django.shortcuts import (
    render, get_object_or_404, redirect, get_list_or_404
    )
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy, reverse
from django.forms import formset_factory
from django.contrib import messages
from django.db.models import Q, Sum, F, Count, Value
from django.db.models.functions import Concat
from urllib.parse import urlencode
from .models import (
    Competition, Game, LineupEntry, PlayerStatLine, InningScore,
    Substitution
    )
from players.models import Players
from .forms import (
    CompetitionForm, GameForm, LineupEntryForm, SubstitutionForm,
    InningScoreForm, BattingStatForm, PitchDefStatForm,
    InningScoreFormSet, BattingStatFormSet, PitchDefStatFormSet,
    CompetitionSelectForm
    )

class CompetitionListView(ListView):
    model = Competition
    template_name = 'stats/competition_list.html'

class CompetitionCreateView(CreateView):
    model = Competition
    form_class = CompetitionForm
    template_name = 'stats/competition_form.html'
    success_url = reverse_lazy('stats:competition-list')

# class GameCreateView(CreateView):
#     model = Game
#     form_class = GameForm
#     template_name = 'stats/game_form.html'
#     success_url = reverse_lazy('stats:competition-list')  # Or maybe later: competition detail

def create_game_view(request):
    if request.method == 'POST':
        form = GameForm(request.POST)
        if form.is_valid():
            game = form.save(commit=False)
            game.status = 'draft'  # Make sure new games start as draft
            game.save()
            return redirect('stats:game-select')
    else:
        form = GameForm()
    
    return render(request, 'stats/create_game.html', {'form': form})


def delete_game_view(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    if game.status == 'final':
        messages.error(request, "You cannot delete a finalized game.")
        return redirect('stats:game-select')

    # Delete all related stats
    LineupEntry.objects.filter(game=game).delete()
    Substitution.objects.filter(game=game).delete()
    InningScore.objects.filter(game=game).delete()
    PlayerStatLine.objects.filter(game=game).delete()

    game.delete()
    messages.success(request, "Game and related data deleted.")
    return redirect('stats:game-select')


def finalize_game_view(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    if game.status == 'final':
        messages.info(request, "This game is already finalized.")
    else:
        game.status = 'final'
        game.save()
        messages.success(request, "Game finalized and locked.")

    return redirect('stats:game-select')


# class GameSelectView(ListView):
#     model = Game
#     template_name = 'stats/game_select.html'
#     context_object_name = 'games'

def game_select_view(request):
    games = Game.objects.select_related('home_team', 'away_team').order_by('-date_played')

    return render(request, 'stats/game_select.html', {
        'games': games
    })


def enter_lineups_view(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    if game.status == 'final':
        messages.error(request, "This game is finalized and cannot be edited.")
        return redirect('stats:game-select')

    if request.method == 'POST':
        home_form = LineupEntryForm(request.POST, team=game.home_team, prefix='home')
        away_form = LineupEntryForm(request.POST, team=game.away_team, prefix='away')

        if home_form.is_valid() and away_form.is_valid():
            # Create batting order entries (1–9)
            for i in range(1, 10):
                LineupEntry.objects.create(
                    game=game,
                    team=game.home_team,
                    player=home_form.cleaned_data[f'player_{i}'],
                    batting_order=i,
                    fielding_position=home_form.cleaned_data[f'position_{i}'],
                    is_starting=True
                )
                LineupEntry.objects.create(
                    game=game,
                    team=game.away_team,
                    player=away_form.cleaned_data[f'player_{i}'],
                    batting_order=i,
                    fielding_position=away_form.cleaned_data[f'position_{i}'],
                    is_starting=True
                )

            # Create starting pitcher entries (batting_order can be None or 0)
            LineupEntry.objects.create(
                game=game,
                team=game.home_team,
                player=home_form.cleaned_data['starting_pitcher'],
                batting_order=None,
                fielding_position='P',
                is_starting=True
            )
            LineupEntry.objects.create(
                game=game,
                team=game.away_team,
                player=away_form.cleaned_data['starting_pitcher'],
                batting_order=None,
                fielding_position='P',
                is_starting=True
            )

            return redirect('stats:game-select')
    else:
        home_form = LineupEntryForm(team=game.home_team, prefix='home')
        away_form = LineupEntryForm(team=game.away_team, prefix='away')

    # Once you have home_form and away_form, build these lists:
    home_batting = [
        (home_form[f'player_{i}'], home_form[f'position_{i}'])
        for i in range(1, 10)
    ]
    away_batting = [
        (away_form[f'player_{i}'], away_form[f'position_{i}'])
        for i in range(1, 10)
    ]

    return render(request, 'stats/enter_lineups.html', {
        'game': game,
        'home_form': home_form,
        'away_form': away_form,
        'home_batting': home_batting,
        'away_batting': away_batting,
    })


def enter_statlines_view(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    # Step 1a: seed statlines for starters
    lineup_entries = (
        LineupEntry.objects
        .filter(game=game)
        .select_related('player', 'team')
    )
    for entry in lineup_entries:
        team = entry.team
        if not team:
            # shouldn’t happen if your LineupEntry always has a team
            continue

        PlayerStatLine.objects.get_or_create(
            game=game,
            player=entry.player,
            team=team,
            defaults={
                'position': entry.fielding_position,
                # batting defaults
                'ab': 0, 'r': 0, 'h': 0, 'doubles': 0, 'triples': 0,
                'hr': 0, 'rbi': 0, 'bb': 0, 'so': 0, 'sf': 0,
                'hbp': 0, 'sb': 0, 'cs': 0, 'dp': 0,
                # pitching defaults (IP stored as outs, e.g. 0)
                'ip_outs': 0, 'ra': 0, 'er': 0, 'h_allowed': 0,
                'bb_allowed': 0, 'k_thrown': 0,
                'decision': '',
                'hb': 0, 'balk': 0, 'wp': 0, 'ibb': 0,
                # defense defaults
                'po': 0, 'a': 0, 'e': 0, 'pb': 0,
            }
        )

    # Step 1b: seed statlines for subs
    subs = (
        Substitution.objects
        .filter(game=game)
        .select_related('player_in', 'team')
    )
    for sub in subs:
        team = sub.team
        if not team:
            continue

        PlayerStatLine.objects.get_or_create(
            game=game,
            player=sub.player_in,
            team=team,
            defaults={
                'position': sub.position,
                # same defaults as above…
                'ab': 0, 'r': 0, 'h': 0, 'doubles': 0, 'triples': 0,
                'hr': 0, 'rbi': 0, 'bb': 0, 'so': 0, 'sf': 0,
                'hbp': 0, 'sb': 0, 'cs': 0, 'dp': 0,
                'ip_outs': 0, 'ra': 0, 'er': 0, 'h_allowed': 0,
                'bb_allowed': 0, 'k_thrown': 0,
                'decision': '',
                'hb': 0, 'balk': 0, 'wp': 0, 'ibb': 0,
                'po': 0, 'a': 0, 'e': 0, 'pb': 0,
            }
        )

    # Step 2: load all statlines for this game
    statlines = (
        PlayerStatLine.objects
        .filter(game=game)
        .select_related('player', 'team')
        .order_by('team__serial', 'player__last_name')
    )

    # Step 3: bind formsets
    if request.method == 'POST':
        batting_formset = BattingStatFormSet(
            request.POST, queryset=statlines, prefix='bat'
        )
        pitchdef_formset = PitchDefStatFormSet(
            request.POST, queryset=statlines, prefix='pitchdef'
        )

        # … your “restore team” loop …

        # DEBUG: print out why the formset is invalid
        if not batting_formset.is_valid() or not pitchdef_formset.is_valid():
            print("⚠️ Batting errors:", batting_formset.errors)
            print("⚠️ Batting non-form errors:", batting_formset.non_form_errors())
            print("⚠️ Pitching/Def errors:", pitchdef_formset.errors)
            print("⚠️ Pitching/Def non-form errors:", pitchdef_formset.non_form_errors())
        else:
            batting_formset.save()
            pitchdef_formset.save()
            return redirect('stats:game-select')
        
        # restore team on any instance missing it
        for form in batting_formset.forms + pitchdef_formset.forms:
            if form.instance.team_id is None:
                original = next((s for s in statlines if s.pk == form.instance.pk), None)
                if original:
                    form.instance.team = original.team

        if batting_formset.is_valid() and pitchdef_formset.is_valid():
            batting_formset.save()
            pitchdef_formset.save()
            return redirect('stats:game-select')
    else:
        batting_formset = BattingStatFormSet(queryset=statlines, prefix='bat')
        pitchdef_formset = PitchDefStatFormSet(queryset=statlines, prefix='pitchdef')

    # Step 4: split into away vs home by raw FK
    def split_by_team(fs):
        return {
            'away': [f for f in fs if f.instance.team_id == game.away_team.serial],
            'home': [f for f in fs if f.instance.team_id == game.home_team.serial],
        }

    batting_split = split_by_team(batting_formset)
    pitchdef_split = split_by_team(pitchdef_formset)

    # Step 5: zip batting + pitching forms
    batting_pitchdef = {
        'away': list(zip(batting_split['away'], pitchdef_split['away'])),
        'home': list(zip(batting_split['home'], pitchdef_split['home'])),
    }

    return render(request, 'stats/enter_statlines.html', {
        'game': game,
        'batting_pitchdef_forms': batting_pitchdef,
        'batting_mgmt': batting_formset.management_form,
        'pitchdef_mgmt': pitchdef_formset.management_form,
    })


def enter_substitutions(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    # Determine which team we’re subbing for — can pass in via query param
    team_side = request.GET.get('team')  # 'home' or 'away'
    if team_side == 'home':
        team = game.home_team
    elif team_side == 'away':
        team = game.away_team
    else:
        messages.error(request, "Team not specified.")
        return redirect('stats:game-select')

    if request.method == 'POST':
        form = SubstitutionForm(request.POST, team=team)
        if form.is_valid():
            substitution = form.save(commit=False)
            substitution.game = game
            substitution.team = team
            substitution.save()
            return redirect('stats:enter-substitutions', game_id=game.id)
    else:
        form = SubstitutionForm(team=team)

    return render(request, 'stats/enter_substitutions.html', {
        'form': form,
        'game': game,
        'team': team
    })


def enter_inning_scores(request, game_id):
    game = get_object_or_404(Game, pk=game_id)
    MAX_INNINGS = 9

    # On GET, make sure we have rows for each inning/team
    if request.method == 'GET':
        for team in (game.away_team, game.home_team):
            for inn in range(1, MAX_INNINGS + 1):
                InningScore.objects.get_or_create(
                    game=game,
                    team=team,
                    inning=inn,
                    defaults={'runs': 0}
                )

    # Now build formsets over those rows
    home_qs = InningScore.objects.filter(game=game, team=game.home_team).order_by('inning')
    away_qs = InningScore.objects.filter(game=game, team=game.away_team).order_by('inning')

    if request.method == 'POST':
        home_formset = InningScoreFormSet(request.POST, prefix='home', queryset=home_qs)
        away_formset = InningScoreFormSet(request.POST, prefix='away', queryset=away_qs)


        if not home_formset.is_valid() or not away_formset.is_valid():
            print("🏳️ home errors:", home_formset.errors)
            print("🏳️ home non-form errors:", home_formset.non_form_errors())
            print("🏳️ away errors:", away_formset.errors)
            print("🏳️ away non-form errors:", away_formset.non_form_errors())
        else:
            home_formset.save()
            away_formset.save()
            return redirect('stats:game-select')


        if home_formset.is_valid() and away_formset.is_valid():
            home_formset.save()
            away_formset.save()
            return redirect('stats:game-select')
    else:
        home_formset = InningScoreFormSet(prefix='home', queryset=home_qs)
        away_formset = InningScoreFormSet(prefix='away', queryset=away_qs)

    return render(request, 'stats/enter_inning_scores.html', {
        'game': game,
        'home_formset': home_formset,
        'away_formset': away_formset,
        'home_team': game.home_team,
        'away_team': game.away_team,
    })


def enter_enhanced_stats(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    # 1a: pull every player who has a lineup entry this game
    lineup_entries = LineupEntry.objects.filter(game=game)
    for entry in lineup_entries:
        # create a stat‐line for this player/team if it doesn't exist yet
        PlayerStatLine.objects.get_or_create(
            game=game,
            player=entry.player,
            team=entry.team,
            defaults={
                'pa': 0, 'ab': 0, 'h': 0,  'r': 0, 'rbi': 0,
                'bb': 0, 'k': 0,  'hr': 0, 'sb': 0, 'cs': 0,
                'ip': 0.0, 'er': 0, 'h_allowed': 0, 'bb_allowed': 0,
                'k_thrown': 0, 'decision': '',
                'po': 0, 'a': 0, 'e': 0, 'position': entry.fielding_position
            }
        )

    # 1b: build a formset over those rows
    EnhancedFormSet = modelformset_factory(
        PlayerStatLine,
        form=EnhancedStatForm,
        extra=0,
        can_delete=False
    )
    qs = PlayerStatLine.objects.filter(game=game).order_by('team__id', 'player__last_name')

    if request.method == 'POST':
        formset = EnhancedFormSet(request.POST, queryset=qs, prefix='enh')
        if formset.is_valid():
            formset.save()
            return redirect('stats:game-select')
    else:
        formset = EnhancedFormSet(queryset=qs, prefix='enh')

    return render(request, 'stats/enter_enhanced_stats.html', {
        'game': game,
        'formset': formset,
    })


def competition_select_view(request):
    form = CompetitionSelectForm(request.GET or None)
    if request.method == 'GET' and form.is_valid() and form.cleaned_data['competitions']:
        # build ?competitions=1&competitions=2…
        qs = urlencode([('competitions', c.pk) for c in form.cleaned_data['competitions']])
        return redirect(f"{reverse('stats:competition-menu')}?{qs}")

    return render(request, 'stats/competition_select.html', {
        'form': form,
    })


def competition_menu_view(request):
    # read back the GET parameters
    comp_ids = request.GET.getlist('competitions')
    competitions = get_list_or_404(Competition, pk__in=comp_ids)

    # build a URL-encoded slug to forward on each menu link
    qs = request.GET.urlencode()

    return render(request, 'stats/competition_menu.html', {
        'competitions': competitions,
        'qs': qs,
    })


def competition_player_stats_view(request):
    comp_ids = request.GET.getlist('competitions')
    qs = PlayerStatLine.objects.filter(game__competition__in=comp_ids)
    stats = (
        qs.values('player__first_name', 'player__last_name')
          .annotate(ab=Sum('ab'), h=Sum('h'), rbi=Sum('rbi'), hr=Sum('hr'))
          .order_by('-h')
    )
    return render(request, 'stats/competition_player_stats.html', {
        'stats': stats,
        'qs': request.GET.urlencode(),
    })


def competition_team_stats_view(request):
    comp_ids = request.GET.getlist('competitions')
    competitions = get_list_or_404(Competition, pk__in=comp_ids)

    stats = (
        PlayerStatLine.objects
        .filter(game__competition__in=competitions)
        # Make sure to include every non-aggregated column here:
        .values(
            'team__serial',
            'team__first_name',
            'team__team_name',
        )
        .annotate(
            team_serial=F('team__serial'),
            team_name=Concat(
                F('team__first_name'),
                Value(' '),
                F('team__team_name')
            ),
            ab=Sum('ab'),
            h=Sum('h'),
            r=Sum('r'),
            rbi=Sum('rbi'),
            hr=Sum('hr'),
            bb=Sum('bb'),
            so=Sum('so'),        # <-- strikeouts is 'so', not 'k'
            hbp=Sum('hbp'),
            doubles=Sum('doubles'),
            triples=Sum('triples'),
            sb=Sum('sb'),
            cs=Sum('cs'),
            dp=Sum('dp'),
            # …any other offensive sums you need…
        )
        .order_by('-h')
    )

    return render(request, 'stats/competition_team_stats.html', {
        'stats': stats,
        'qs': request.GET.urlencode(),
        'competitions': competitions,
    })


def competition_leaders_view(request):
    comp_ids = request.GET.getlist('competitions')
    competitions = get_list_or_404(Competition, pk__in=comp_ids)

    qs = PlayerStatLine.objects.filter(game__competition__in=competitions)
    # Leading batting average (min 10 AB)
    leaders = (
        qs.values('player__first_name', 'player__last_name')
          .annotate(
              ab=Sum('ab'),
              h=Sum('h'),
              avg=F('h') * 1.0 / F('ab')
          )
          .filter(ab__gte=10)
          .order_by('-avg')[:20]
    )

    return render(request, 'stats/competition_leaders.html', {
        'leaders': leaders,
        'qs': request.GET.urlencode(),
        'competitions': competitions,
    })


def competition_standings_view(request):
    comp_ids = request.GET.getlist('competitions')
    competitions = get_list_or_404(Competition, pk__in=comp_ids)

    # Sum wins/losses/ties from TeamStanding across all comps
    standings = (
        TeamStanding.objects
        .filter(competition__in=competitions)
        .values('team__first_name', 'team__team_name')
        .annotate(
            wins=Sum('wins'),
            losses=Sum('losses'),
            ties=Sum('ties')
        )
        .order_by('-wins', 'losses')
    )

    return render(request, 'stats/competition_standings.html', {
        'standings': standings,
        'qs': request.GET.urlencode(),
        'competitions': competitions,
    })


def competition_games_view(request):
    comp_ids = request.GET.getlist('competitions')
    competitions = get_list_or_404(Competition, pk__in=comp_ids)

    games = Game.objects.filter(competition__in=competitions).order_by('date_played')

    return render(request, 'stats/competition_games.html', {
        'games': games,
        'qs': request.GET.urlencode(),
        'competitions': competitions,
    })
