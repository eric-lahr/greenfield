from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.forms import formset_factory
from .models import Competition, Game, LineupEntry
from .forms import CompetitionForm, GameForm, LineupEntryForm  # Create this

class CompetitionListView(ListView):
    model = Competition
    template_name = 'stats/competition_list.html'

class CompetitionCreateView(CreateView):
    model = Competition
    form_class = CompetitionForm
    template_name = 'stats/competition_form.html'
    success_url = reverse_lazy('stats:competition-list')

class GameCreateView(CreateView):
    model = Game
    form_class = GameForm
    template_name = 'stats/game_form.html'
    success_url = reverse_lazy('stats:competition-list')  # Or maybe later: competition detail

class GameSelectView(ListView):
    model = Game
    template_name = 'stats/game_select.html'
    context_object_name = 'games'


def enter_lineups_view(request, game_id):
    game = get_object_or_404(Game, pk=game_id)

    if request.method == 'POST':
        home_form = LineupEntryForm(request.POST, team=game.home_team)
        away_form = LineupEntryForm(request.POST, team=game.away_team)

        if home_form.is_valid() and away_form.is_valid():
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
            return redirect('stats:game-select')  # or wherever
    else:
        home_form = LineupEntryForm(team=game.home_team)
        away_form = LineupEntryForm(team=game.away_team)

    return render(request, 'stats/enter_lineups.html', {
        'game': game,
        'home_form': home_form,
        'away_form': away_form
    })