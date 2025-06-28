from django.shortcuts import (
    render, get_object_or_404, redirect, get_list_or_404
    )
from django.views.generic import ListView, CreateView, FormView, DetailView
from django.views import View
from django.urls import reverse_lazy, reverse
from django.forms import formset_factory
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import (
    Q, Sum, F, Count, Value, FloatField, ExpressionWrapper,
    Case, When, IntegerField, When
    )
from django.db.models.functions import Concat
from urllib.parse import urlencode
from .models import (
    Competition, Game, LineupEntry, PlayerStatLine, InningScore,
    Substitution, League, Division, TeamEntry, TeamStanding
    )
from players.models import Players
from teams.models import Teams
from .forms import (
    CompetitionForm, GameForm, LineupEntryForm, SubstitutionForm,
    InningScoreForm, BattingStatForm, PitchDefStatForm,
    InningScoreFormSet, BattingStatFormSet, PitchDefStatFormSet,
    CompetitionSelectForm, LeagueCountForm, LeagueForm, DivisionForm,
    DivisionCountForm, TeamEntryForm
    )


def competition_teams_json(request, pk):
    comp = get_object_or_404(Competition, pk=pk)

    if comp.has_structure:
        # Gather all team‐IDs that have a TeamEntry for this competition
        team_ids = (
            TeamEntry.objects
            .filter(competition=comp)
            .values_list('team_id', flat=True)
            .distinct()
        )
        qs = Teams.objects.filter(pk__in=team_ids)
    else:
        qs = Teams.objects.all()

    teams = [{'pk': t.pk, 'display': str(t)} for t in qs]
    return JsonResponse({'teams': teams})


class CompetitionListView(ListView):
    model = Competition
    template_name = 'competitions/competition_list.html'

class CompetitionCreateView(CreateView):
    model         = Competition
    form_class    = CompetitionForm
    template_name = 'competitions/competition_form.html'

    def form_valid(self, form):
        # Save the Competition
        comp = form.save()

        # If they want a structure, send them to the league‐count step
        if comp.has_structure:
            return redirect('stats:league-count', pk=comp.pk)

        # Otherwise, go straight to the competition detail page
        return redirect('stats:competition-detail', pk=comp.pk)

class CompetitionDetailView(DetailView):
    model = Competition
    template_name = 'competitions/competition_detail.html'
    context_object_name = 'competition'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        comp = self.object

        if comp.has_structure:
            # teams added directly to the competition
            ctx['comp_teams'] = comp.teams.filter(
                team_entries__competition=comp,
                team_entries__league__isnull=True,
                team_entries__division__isnull=True
            )
            # all leagues under this competition
            ctx['leagues'] = comp.leagues.all()
        else:
            # unstructured: all teams go here
            ctx['teams'] = comp.teams.all()

        return ctx

class LeagueCountView(FormView):
    form_class    = LeagueCountForm
    template_name = "competitions/league_count.html"

    def dispatch(self, request, *args, **kwargs):
        self.comp = Competition.objects.get(pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **ctx):
        ctx = super().get_context_data(**ctx)
        ctx['comp'] = self.comp
        return ctx

    def form_valid(self, form):
        num = form.cleaned_data['num_leagues']
        # redirect into the league‐creation step with the ?num=… querystring
        return redirect(
            reverse('stats:league-add', args=[self.comp.pk]) + f'?num={num}'
        )

class LeagueCreateView(View):
    def get(self, request, pk):
        comp = get_object_or_404(Competition, pk=pk)
        num  = int(request.GET.get('num', 1))
        LeagueFormSet = formset_factory(LeagueForm, extra=num)
        formset = LeagueFormSet()
        return render(request, 'competitions/league_formset.html', {
            'competition': comp,
            'formset': formset,
        })

    def post(self, request, pk):
        comp = get_object_or_404(Competition, pk=pk)
        num  = int(request.GET.get('num', 1))
        LeagueFormSet = formset_factory(LeagueForm, extra=num)
        formset = LeagueFormSet(request.POST)

        if formset.is_valid():
            for form in formset:
                league = form.save(commit=False)
                league.competition = comp
                league.save()

            # ← HERE: redirect back to the CompetitionDetailView
            return redirect('stats:competition-detail', pk=comp.pk)

        return render(request, 'competitions/league_formset.html', {
            'competition': comp,
            'formset': formset,
        })

class DivisionCountView(FormView):
    form_class    = DivisionCountForm
    template_name = "competitions/division_count.html"

    def dispatch(self, request, *args, **kwargs):
        # stash the League object for use in get_context_data & redirect
        self.league = get_object_or_404(League, pk=kwargs['league_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **ctx):
        ctx = super().get_context_data(**ctx)
        ctx['league'] = self.league
        return ctx

    def form_valid(self, form):
        num = form.cleaned_data['num_divisions']
        # redirect into your DivisionCreateView, passing ?num=… just like leagues
        url = reverse('stats:division-add', args=[self.league.pk])
        return redirect(f"{url}?num={num}")

class DivisionCreateView(View):
    """
    Renders a formset to create N divisions for a given league,
    then saves them and redirects back to the competition detail.
    """
    def get(self, request, league_pk):
        league = get_object_or_404(League, pk=league_pk)
        num = int(request.GET.get('num', 1))
        DivisionFormSet = formset_factory(DivisionForm, extra=num)
        formset = DivisionFormSet()
        return render(request, 'competitions/division_formset.html', {
            'league': league,
            'formset': formset,
        })

    def post(self, request, league_pk):
        league = get_object_or_404(League, pk=league_pk)
        num = int(request.GET.get('num', 1))
        DivisionFormSet = formset_factory(DivisionForm, extra=num)
        formset = DivisionFormSet(request.POST)

        if formset.is_valid():
            for form in formset:
                division = form.save(commit=False)
                division.league = league
                division.save()
            # once divisions exist, go back to the competition overview
            return redirect('stats:competition-detail', pk=league.competition.pk)

        # if invalid, re-render the same formset with errors
        return render(request, 'competitions/division_formset.html', {
            'league': league,
            'formset': formset,
        })


def create_game(request):
    if request.method == 'POST':
        form = GameForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('stats:competition-games')  # or wherever
    else:
        form = GameForm(request.GET or None)

    return render(request, 'stats/game_form.html', {
        'form': form
    })


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

    # Read how many extra innings to show (default 0)
    try:
        extra = int(request.GET.get('extra', 0))
    except ValueError:
        extra = 0
    total_innings = MAX_INNINGS + extra

    # On GET, make sure we have rows 1..total_innings
    if request.method == 'GET':
        for team in (game.away_team, game.home_team):
            for inn in range(1, total_innings + 1):
                InningScore.objects.get_or_create(
                    game=game,
                    team=team,
                    inning=inn,
                    defaults={'runs': 0}
                )
    # … the rest remains the same …


    # Now build formsets over those rows
    home_qs = InningScore.objects.filter(game=game, team=game.home_team).order_by('inning')
    away_qs = InningScore.objects.filter(game=game, team=game.away_team).order_by('inning')
    
    if request.method == 'POST':
        home_formset = InningScoreFormSet(request.POST, prefix='home', queryset=home_qs)
        away_formset = InningScoreFormSet(request.POST, prefix='away', queryset=away_qs)

        if home_formset.is_valid() and away_formset.is_valid():
            # 1) save the per-inning rows
            home_formset.save()
            away_formset.save()

            # 2) re-sum all innings for each team
            home_total = InningScore.objects.filter(
                game=game, team=game.home_team
            ).aggregate(total=Sum('runs'))['total'] or 0

            away_total = InningScore.objects.filter(
                game=game, team=game.away_team
            ).aggregate(total=Sum('runs'))['total'] or 0

            # 3) update the Game record
            game.home_score = home_total
            game.away_score = away_total
            game.save()

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


# def enter_enhanced_stats(request, game_id):
#     game = get_object_or_404(Game, pk=game_id)

#     # 1a: pull every player who has a lineup entry this game
#     lineup_entries = LineupEntry.objects.filter(game=game)
#     for entry in lineup_entries:
#         # create a stat‐line for this player/team if it doesn't exist yet
#         PlayerStatLine.objects.get_or_create(
#             game=game,
#             player=entry.player,
#             team=entry.team,
#             defaults={
#                 'pa': 0, 'ab': 0, 'h': 0,  'r': 0, 'rbi': 0,
#                 'bb': 0, 'k': 0,  'hr': 0, 'sb': 0, 'cs': 0,
#                 'ip': 0.0, 'er': 0, 'h_allowed': 0, 'bb_allowed': 0,
#                 'k_thrown': 0, 'decision': '',
#                 'po': 0, 'a': 0, 'e': 0, 'position': entry.fielding_position
#             }
#         )

#     # 1b: build a formset over those rows
#     EnhancedFormSet = modelformset_factory(
#         PlayerStatLine,
#         form=EnhancedStatForm,
#         extra=0,
#         can_delete=False
#     )
#     qs = PlayerStatLine.objects.filter(game=game).order_by('team__id', 'player__last_name')

#     if request.method == 'POST':
#         formset = EnhancedFormSet(request.POST, queryset=qs, prefix='enh')
#         if formset.is_valid():
#             formset.save()
#             return redirect('stats:game-select')
#     else:
#         formset = EnhancedFormSet(queryset=qs, prefix='enh')

#     return render(request, 'stats/enter_enhanced_stats.html', {
#         'game': game,
#         'formset': formset,
#     })


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
    comp_ids     = request.GET.getlist('competitions')
    competitions = get_list_or_404(Competition, pk__in=comp_ids)

    # only teams in this competition
    played_teams = Teams.objects.filter(
        Q(home_games__competition__in=competitions) |
        Q(away_games__competition__in=competitions)
    ).distinct()

    # optional team filter
    team_serial = request.GET.get('team')

    # base queryset of stat lines, optionally filtered by team
    base_qs = PlayerStatLine.objects.filter(
        game__competition__in=competitions,
        team__in=played_teams
    )
    if team_serial:
        base_qs = base_qs.filter(team__serial=team_serial)

    # ——— Batters ———
    offense_stats = (
        base_qs
        .values('player__serial', 'player__first_name', 'player__last_name')
        .annotate(
            player_id=F('player__serial'),
            name=Concat(F('player__first_name'), Value(' '), F('player__last_name')),
            games=Count('game', distinct=True),
            ab=Sum('ab'),
            bb=Sum('bb'),
            h=Sum('h'),
            r=Sum('r'),
            rbi=Sum('rbi'),
            hr=Sum('hr'),
            so=Sum('so'),
            sb=Sum('sb'),
            cs=Sum('cs'),
            hbp=Sum('hbp'),
            doubles=Sum('doubles'),
            triples=Sum('triples'),
            dp=Sum('dp'),
            sf=Sum('sf'),
        )
        # drop players with no AB and no BB
        .filter(Q(ab__gt=0) | Q(bb__gt=0))
        .annotate(
            avg=Case(
                When(ab__gt=0,
                     then=ExpressionWrapper(F('h') * 1.0 / F('ab'),
                                            output_field=FloatField())),
                default=Value(0),
                output_field=FloatField()
            ),
            obp_denom=ExpressionWrapper(
                F('ab') + F('bb') + F('hbp') + F('sf'),
                output_field=FloatField()
            )
        )
        .annotate(
            obp=Case(
                When(obp_denom__gt=0,
                     then=ExpressionWrapper(
                         (F('h') + F('bb') + F('hbp')) * 1.0 / F('obp_denom'),
                         output_field=FloatField()
                     )
                ),
                default=Value(0),
                output_field=FloatField()
            ),
            slg=Case(
                When(ab__gt=0,
                     then=ExpressionWrapper(
                         (
                             (F('h') - F('doubles') - F('triples') - F('hr'))
                             + 2 * F('doubles')
                             + 3 * F('triples')
                             + 4 * F('hr')
                         ) * 1.0 / F('ab'),
                         output_field=FloatField()
                     )
                ),
                default=Value(0),
                output_field=FloatField()
            ),
            ops=ExpressionWrapper(F('obp') + F('slg'), output_field=FloatField()),
        )
        .order_by('-games', 'player__last_name')
    )

    # ——— Pitchers ———
    pitching_stats = (
        base_qs
        .filter(ip_outs__gt=0)
        .values('player__serial', 'player__first_name', 'player__last_name')
        .annotate(
            player_id=F('player__serial'),
            name=Concat(F('player__first_name'), Value(' '), F('player__last_name')),
            games=Count('game', distinct=True),
            wins=Sum(Case(When(decision='W', then=1), default=0)),
            losses=Sum(Case(When(decision='L', then=1), default=0)),
            saves=Sum(Case(When(decision='S', then=1), default=0)),
            ip_outs=Sum('ip_outs'),
            er=Sum('er'),
            h_allowed=Sum('h_allowed'),
            bb_allowed=Sum('bb_allowed'),
            k_thrown=Sum('k_thrown'),
        )
        .annotate(
            innings_pitched=ExpressionWrapper(F('ip_outs') * 1.0 / 3.0,
                                              output_field=FloatField())
        )
        .annotate(
            era=ExpressionWrapper(F('er') * 9.0 / F('innings_pitched'),
                                  output_field=FloatField()),
            whip=ExpressionWrapper(
                (F('bb_allowed') + F('h_allowed')) * 1.0 / F('innings_pitched'),
                output_field=FloatField()
            ),
        )
        .order_by('-innings_pitched')
    )

    # ——— Defense ———
    defense_stats = (
        base_qs
        .values('player__serial', 'player__first_name', 'player__last_name')
        .annotate(
            player_id=F('player__serial'),
            name=Concat(F('player__first_name'), Value(' '), F('player__last_name')),
            po=Sum('po'),
            a=Sum('a'),
            e=Sum('e'),
            pb=Sum('pb'),
        )
        .annotate(
            chances=F('po') + F('a') + F('e'),
        )
        .order_by('-chances', 'player__last_name')
    )

    return render(request, 'stats/competition_player_stats.html', {
        'competitions':  competitions,
        'played_teams':  played_teams,
        'selected_team': team_serial,
        'offense_stats': offense_stats,
        'pitching_stats': pitching_stats,
        'defense_stats': defense_stats,
        'qs':            request.GET.urlencode(),
    })


def competition_team_stats_view(request):
    comp_ids      = request.GET.getlist('competitions')
    competitions  = get_list_or_404(Competition, pk__in=comp_ids)

    # ——— Offense ———
    base_qs = (
        PlayerStatLine.objects
        .filter(game__competition__in=competitions)
        .values('team__serial','team__first_name','team__team_name')
        .annotate(
            team_serial=F('team__serial'),
            team_name=Concat(F('team__first_name'), Value(' '), F('team__team_name')),
            ab=Sum('ab'), h=Sum('h'), r=Sum('r'), rbi=Sum('rbi'),
            hr=Sum('hr'), bb=Sum('bb'), so=Sum('so'), sb=Sum('sb'),
            cs=Sum('cs'), hbp=Sum('hbp'), doubles=Sum('doubles'),
            triples=Sum('triples'), dp=Sum('dp'), sf=Sum('sf'),
        )
    )
    offense_stats = base_qs.annotate(
        avg=ExpressionWrapper(F('h')*1.0/F('ab'), output_field=FloatField()),
        obp=ExpressionWrapper((F('h')+F('bb')+F('hbp'))*1.0/
                              (F('ab')+F('bb')+F('hbp')+F('sf')),
                              output_field=FloatField()),
        slg=ExpressionWrapper(
            ((F('h')-F('doubles')-F('triples')-F('hr'))
             +F('doubles')*2+F('triples')*3+F('hr')*4)*1.0/F('ab'),
            output_field=FloatField()),
        ops=ExpressionWrapper(F('obp') + F('slg'), output_field=FloatField()),
    ).order_by('-ops')

    # ——— Pitching ———
    pitching_stats = (
        PlayerStatLine.objects
        .filter(game__competition__in=competitions)
        .values('team__serial', 'team__first_name', 'team__team_name')
        .annotate(
            team_serial=F('team__serial'),
            team_name=Concat(F('team__first_name'), Value(' '), F('team__team_name')),
            ip_outs=Sum('ip_outs'),
            er=Sum('er'),
            h_allowed=Sum('h_allowed'),
            bb_allowed=Sum('bb_allowed'),
            k_thrown=Sum('k_thrown'),
            hb=Sum('hb'),
            hra=Sum('hra'),
            balk=Sum('balk'),
            wp=Sum('wp'),
            ibb=Sum('ibb'),
        )
        .annotate(
            innings_pitched=ExpressionWrapper(
                F('ip_outs') * 1.0 / 3.0,
                output_field=FloatField()
            )
        )
        .annotate(
            era=ExpressionWrapper(
                F('er') * 9.0 / F('innings_pitched'),
                output_field=FloatField()
            ),
            whip=ExpressionWrapper(
                (F('bb_allowed') + F('h_allowed')) * 1.0 / F('innings_pitched'),
                output_field=FloatField()
            ),
        )
        .order_by('team_name')
    )

    # ——— Defense ———
    defense_stats = (
        PlayerStatLine.objects
        .filter(game__competition__in=competitions)
        .values('team__serial','team__first_name','team__team_name')
        .annotate(
            team_serial=F('team__serial'),
            team_name=Concat(F('team__first_name'), Value(' '), F('team__team_name')),
            po=Sum('po'),
            a=Sum('a'),
            e=Sum('e'),
            pb=Sum('pb'),
            dp=Sum('dp'),
        )
        .annotate(
            total_chances=F('po') + F('a') + F('e'),
        )
        .annotate(
            fld_pct=Case(
                When(total_chances=0, then=Value(0.0)),
                default=(F('po') + F('a')) * Value(1.0) / F('total_chances'),
                output_field=FloatField(),
            )
        )
        .order_by('team_name')
    )

    return render(request, 'stats/competition_team_stats.html', {
        'offense_stats':   offense_stats,
        'pitching_stats':  pitching_stats,
        'defense_stats':   defense_stats,
        'qs':              request.GET.urlencode(),
        'competitions':    competitions,
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
    comp_id     = request.GET.get('competitions')
    competition = get_object_or_404(Competition, pk=comp_id)

    # Build structured or unstructured standings
    if competition.has_structure:
        structured = []
        for league in competition.leagues.all():
            if league.has_divisions:
                divs = []
                for division in league.divisions.all():
                    qs = Teams.objects.filter(
                        team_entries__competition=competition,
                        team_entries__division=division
                    )
                    divs.append({
                        'name': division.name,
                        'rows': _annotate_standings(qs, competition)
                    })
                structured.append({'name': league.name, 'divisions': divs})
            else:
                qs = Teams.objects.filter(
                    team_entries__competition=competition,
                    team_entries__league=league
                )
                structured.append({
                    'name': league.name,
                    'rows': _annotate_standings(qs, competition)
                })
        context = {'competition': competition, 'structured': structured}
    else:
        qs = Teams.objects.filter(team_entries__competition=competition)
        rows = _annotate_standings(qs, competition)
        context = {'competition': competition, 'unstructured': rows}

    return render(request, 'stats/competition_standings.html', context)


def _annotate_standings(qs, competition):
    """
    Annotate a Teams queryset with wins, losses, GB, and pct.
    Returns a list of dicts: {'display_name','wins','losses','gb','win_pct'}.
    """
    annotated = (
        qs.annotate(
            display_name=Concat(F('first_name'), Value(' '), F('team_name')),
            played=Count('home_games', filter=Q(home_games__competition=competition)) +
                   Count('away_games', filter=Q(away_games__competition=competition)),
            wins=Count('home_games', filter=Q(
                        home_games__competition=competition,
                        home_games__home_score__gt=F('home_games__away_score')
                    )) +
                 Count('away_games', filter=Q(
                        away_games__competition=competition,
                        away_games__away_score__gt=F('away_games__home_score')
                    )),
            losses=Count('home_games', filter=Q(
                        home_games__competition=competition,
                        home_games__home_score__lt=F('home_games__away_score')
                    )) +
                   Count('away_games', filter=Q(
                        away_games__competition=competition,
                        away_games__away_score__lt=F('away_games__home_score')
                    )),
        )
        .annotate(
            win_pct=ExpressionWrapper(
                F('wins') * 1.0 / Case(
                    When(played=0, then=Value(1)),   # avoid zero-divide
                    default=F('played'),
                    output_field=FloatField()
                ),
                output_field=FloatField()
            )
        )
        .order_by('-wins', '-win_pct')
    )

    rows = list(annotated.values('display_name', 'wins', 'losses', 'win_pct'))
    if rows:
        leader_wins = rows[0]['wins']
        for row in rows:
            row['gb'] = leader_wins - row['wins']
    return rows


def competition_games_view(request):
    comp_ids = request.GET.getlist('competitions')
    competitions = get_list_or_404(Competition, pk__in=comp_ids)

    games = Game.objects.filter(competition__in=competitions).order_by('date_played')

    return render(request, 'stats/competition_games.html', {
        'games': games,
        'qs': request.GET.urlencode(),
        'competitions': competitions,
    })


def game_boxscore_view(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    # — seed and fetch inning scores as before…
    for team in (game.away_team, game.home_team):
        for inn in range(1, 10):
            InningScore.objects.get_or_create(
                game=game, team=team, inning=inn, defaults={'runs': 0}
            )
    away_scores = list(InningScore.objects.filter(
        game=game, team=game.away_team).order_by('inning'))
    home_scores = list(InningScore.objects.filter(
        game=game, team=game.home_team).order_by('inning'))
    away_total_runs = sum(s.runs for s in away_scores)
    home_total_runs = sum(s.runs for s in home_scores)
    away_total_hits = sum(sl.h for sl in PlayerStatLine.objects.filter(
        game=game, team=game.away_team))
    home_total_hits = sum(sl.h for sl in PlayerStatLine.objects.filter(
        game=game, team=game.home_team))
    away_total_errs = sum(sl.e for sl in PlayerStatLine.objects.filter(
        game=game, team=game.away_team))
    home_total_errs = sum(sl.e for sl in PlayerStatLine.objects.filter(
        game=game, team=game.home_team))

    # — fetch all statlines once —
    statlines = list(PlayerStatLine.objects.filter(game=game)
                     .select_related('player','team'))

    # — build away/home batters in batting order —
    lineup_away = LineupEntry.objects.filter(
        game=game, team=game.away_team
    ).order_by('batting_order').select_related('player')
    lineup_home = LineupEntry.objects.filter(
        game=game, team=game.home_team
    ).order_by('batting_order').select_related('player')

    # only batters (had AB or BB)
    batters = {sl.player.serial: sl for sl in statlines if sl.ab + sl.bb > 0}
    away_batters = [batters[le.player.serial] for le in lineup_away if le.player.serial in batters]
    home_batters = [batters[le.player.serial] for le in lineup_home if le.player.serial in batters]

    # compute AVG/OBP/SLG on each batter
    for sl in batters.values():
        sl.avg = sl.h/sl.ab if sl.ab else 0
        denom = sl.ab + sl.bb + sl.hbp + sl.sf
        sl.obp = (sl.h+sl.bb+sl.hbp)/denom if denom else 0
        singles = sl.h - sl.doubles - sl.triples - sl.hr
        sl.slg = (singles + 2*sl.doubles + 3*sl.triples + 4*sl.hr)/sl.ab if sl.ab else 0
        away_doubles = [
            f"{sl.player.last_name}{f'({sl.doubles})' if sl.doubles>1 else ''}"
            for sl in away_batters if sl.doubles>0
        ]
        home_doubles = [
            f"{sl.player.last_name}{f'({sl.doubles})' if sl.doubles>1 else ''}"
            for sl in home_batters if sl.doubles>0
        ]
        away_triples = [
            f"{sl.player.last_name}{f'({sl.triples})' if sl.triples>1 else ''}"
            for sl in away_batters if sl.triples>0
        ]
        home_triples = [
            f"{sl.player.last_name}{f'({sl.triples})' if sl.triples>1 else ''}"
            for sl in home_batters if sl.triples>0
        ]
        away_hr = [
            f"{sl.player.last_name}{f'({sl.hr})' if sl.hr>1 else ''}"
            for sl in away_batters if sl.hr>0
        ]
        home_hr = [
            f"{sl.player.last_name}{f'({sl.hr})' if sl.hr>1 else ''}"
            for sl in home_batters if sl.hr>0
        ]
        away_sb = [
            f"{sl.player.last_name}{f'({sl.sb})' if sl.sb>1 else ''}"
            for sl in away_batters if sl.sb>0
        ]
        home_sb = [
            f"{sl.player.last_name}{f'({sl.sb})' if sl.sb>1 else ''}"
            for sl in home_batters if sl.sb>0
        ]
        away_cs = [
            f"{sl.player.last_name}{f'({sl.cs})' if sl.cs>1 else ''}"
            for sl in away_batters if sl.cs>0
        ]
        home_cs = [
            f"{sl.player.last_name}{f'({sl.cs})' if sl.cs>1 else ''}"
            for sl in home_batters if sl.cs>0
        ]

    # — fetch all pitcher statlines & compute IP/ERA/WHIP —
    all_pitchers = [sl for sl in statlines if sl.ip_outs > 0]
    for sl in all_pitchers:
        sl.innings_pitched = sl.ip_outs / 3.0
        sl.era = (sl.er * 9.0 / sl.innings_pitched) if sl.innings_pitched else 0
        sl.whip = ((sl.h_allowed + sl.bb_allowed) / sl.innings_pitched) if sl.innings_pitched else 0

    # — fetch pitcher‐substitutions & position‐player substitutions —
    subs = Substitution.objects.filter(game=game).select_related(
        'team','player_in','player_out'
    ).order_by('inning')

    # group by player_out for position subs
    subs_by_out = {}
    for sub in subs:
        if sub.position != 'P':  # position player sub
            subs_by_out.setdefault(sub.player_out.serial, []).append(sub)

    # pitcher subs in order
    away_p_subs = [s for s in subs if s.team == game.away_team and s.position == 'P']
    home_p_subs = [s for s in subs if s.team == game.home_team and s.position == 'P']

    def order_pitchers(team, p_subs):
        roster = [sl for sl in all_pitchers if sl.team == team]
        ordered = []
        # starting pitcher = one not in any p_subs.player_in
        starters = [sl for sl in roster if sl.player not in [s.player_in for s in p_subs]]
        if starters:
            ordered.append(starters[0])
        # then each relief in sub order
        for s in p_subs:
            rel = next((sl for sl in roster if sl.player == s.player_in), None)
            if rel:
                ordered.append(rel)
        return ordered

    away_pitchers = order_pitchers(game.away_team, away_p_subs)
    home_pitchers = order_pitchers(game.home_team, home_p_subs)

    return render(request, 'stats/game_boxscore.html', {
        'game':             game,
        'away_scores':      away_scores,
        'home_scores':      home_scores,
        'away_total_runs':  away_total_runs,
        'home_total_runs':  home_total_runs,
        'away_total_hits':  away_total_hits,
        'home_total_hits':  home_total_hits,
        'away_total_errs':  away_total_errs,
        'home_total_errs':  home_total_errs,
        'away_batters':     away_batters,
        'home_batters':     home_batters,
        'away_pitchers':    away_pitchers,
        'home_pitchers':    home_pitchers,
        'subs_by_out':      subs_by_out,
        'away_doubles':     away_doubles,
        'home_doubles':     home_doubles,
        'away_triples':     away_triples,
        'home_triples':     home_triples,
        'home_hr':          home_hr,
        'away_hr':          away_hr,
        'home_sb':          home_sb,
        'away_sb':          away_sb,
        'home_cs':          home_cs,
        'away_cs':          away_cs
    })


class CompetitionTeamAssignView(CreateView):
    model         = TeamEntry
    form_class    = TeamEntryForm
    template_name = "competitions/teamentry_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.comp = get_object_or_404(Competition, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.competition = self.comp
        form.instance.league      = None
        form.instance.division    = None
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('stats:competition-detail', args=[self.comp.pk])


class LeagueTeamAssignView(CreateView):
    model         = TeamEntry
    form_class    = TeamEntryForm
    template_name = "competitions/teamentry_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.league = get_object_or_404(League, pk=kwargs['league_pk'])
        self.comp   = self.league.competition
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.competition = self.comp
        form.instance.league      = self.league
        form.instance.division    = None
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('stats:competition-detail', args=[self.comp.pk])


class DivisionTeamAssignView(CreateView):
    model         = TeamEntry
    form_class    = TeamEntryForm
    template_name = "competitions/teamentry_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.division = get_object_or_404(Division, pk=kwargs['division_pk'])
        self.league   = self.division.league
        self.comp     = self.league.competition
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.competition = self.comp
        form.instance.league      = self.league
        form.instance.division    = self.division
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('stats:competition-detail', args=[self.comp.pk])


class StandingsView(ListView):
    template_name = 'competitions/standings.html'
    context_object_name = 'standings'

    def get_queryset(self):
        comp = Competition.objects.get(pk=self.kwargs['pk'])
        # gather all teams in this comp
        teams = comp.teams.all()
        # annotate each with totals
        return teams.annotate(
            played=Count('team_entries__game', filter=Q(team_entries__game__competition=comp)),
            wins=Count('team_entries__game', filter=Q(
                team_entries__game__competition=comp,
                team_entries__game__home_team=F('pk'),
                team_entries__game__home_score__gt=F('team_entries__game__away_score')
            )) + Count('team_entries__game', filter=Q(
                team_entries__game__competition=comp,
                team_entries__game__away_team=F('pk'),
                team_entries__game__away_score__gt=F('team_entries__game__home_score')
            )),
            losses=Count('team_entries__game', filter=Q(
                team_entries__game__competition=comp,
                team_entries__game__home_team=F('pk'),
                team_entries__game__home_score__lt=F('team_entries__game__away_score')
            )) + Count('team_entries__game', filter=Q(
                team_entries__game__competition=comp,
                team_entries__game__away_team=F('pk'),
                team_entries__game__away_score__lt=F('team_entries__game__home_score')
            )),
        ).annotate(
            win_pct=ExpressionWrapper(
                F('wins') * 1.0 / F('played'),
                output_field=IntegerField()
            )
        ).order_by('-wins', '-win_pct')
