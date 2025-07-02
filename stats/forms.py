from django import forms
from django.forms import modelformset_factory, formset_factory
from .models import (
    Competition, Game, LineupEntry, PlayerStatLine,
    Substitution, InningScore, League, Division,
    TeamEntry
)
from players.models import Players
from teams.models import Teams
from stats.models import TeamEntry

POSITIONS = [
    ("P", "P"), ("C", "C"), ("1B", "1B"), ("2B", "2B"), ("3B", "3B"),
    ("SS", "SS"), ("LF", "LF"), ("CF", "CF"), ("RF", "RF"), ("DH", "DH"),
]

class LineupEntryForm(forms.Form):
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Grab everyone on this team
        players = Players.objects.filter(team_serial=team) if team else Players.objects.none()

        # Batting order 1–9
        for i in range(1, 10):
            self.fields[f'player_{i}'] = forms.ModelChoiceField(
                queryset=players,
                label=f"Batting #{i}",
                widget=forms.Select(attrs={'class': 'form-control'})
            )
            self.fields[f'position_{i}'] = forms.ChoiceField(
                choices=POSITIONS,
                label=f"Position #{i}",
                widget=forms.Select(attrs={'class': 'form-control'})
            )

        # Now limit to those who actually have a pitching rating
        pitchers = (
            players
            .filter(pitching__isnull=False)   # not null
            .exclude(pitching__exact='')      # not empty string
        )

        self.fields['starting_pitcher'] = forms.ModelChoiceField(
            queryset=pitchers,
            label="Starting Pitcher",
            widget=forms.Select(attrs={'class': 'form-control'})
        )


        # Filter for pitchers only
        # Only those with a non-empty pitching rating
        pitchers = (
            players
            .filter(pitching__isnull=False)   # has a pitching string
            .exclude(pitching__exact='')      # not blank
        )

        self.fields['starting_pitcher'] = forms.ModelChoiceField(
            queryset=pitchers,
            label="Starting Pitcher",
            required=True,
            widget=forms.Select(attrs={'class': 'form-control'})
        )

class CompetitionForm(forms.ModelForm):
    class Meta:
        model = Competition
        fields = ['name', 'abbreviation', 'description', 'has_structure']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class LeagueForm(forms.ModelForm):
    class Meta:
        model = League
        fields = ['name','abbreviation','has_divisions']  # add a has_divisions BooleanField on League if you like.

class LeagueCountForm(forms.Form):
    num_leagues = forms.IntegerField(min_value=1, label="How many leagues?")

class DivisionForm(forms.ModelForm):
    class Meta:
        model = Division
        fields = ['name']

class DivisionCountForm(forms.Form):
    num_divisions = forms.IntegerField(
        min_value=1,
        label="How many divisions?",
    )


# stats/forms.py

from django import forms
from .models      import Game, Competition
from teams.models import Teams

class GameForm(forms.ModelForm):
    competition = forms.ModelChoiceField(
        queryset=Competition.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Competition"
    )
    date_played = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Date"
    )
    home_team = forms.ModelChoiceField(
        queryset=Teams.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Home Team"
    )
    home_score = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        label="Home Score"
    )
    away_team = forms.ModelChoiceField(
        queryset=Teams.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Away Team"
    )
    away_score = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        label="Away Score"
    )
    status = forms.ChoiceField(
        choices=Game.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Status"
    )

    class Meta:
        model  = Game
        fields = [
            'competition',
            'date_played',
            'home_team', 'home_score',
            'away_team', 'away_score',
            'status',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1) figure out comp_id from POST/GET or instance
        comp_id = None
        data    = self.data or {}
        if data.get('competition'):
            comp_id = data.get('competition')
        elif self.instance.pk:
            comp_id = self.instance.competition_id

        # 2) default all teams
        qs = Teams.objects.all()

        # 3) if comp is structured, restrict to its teams
        if comp_id:
            try:
                comp = Competition.objects.get(pk=comp_id)
                if comp.has_structure:
                    qs = comp.teams.all()
            except Competition.DoesNotExist:
                pass

        # 4) apply to both selects
        self.fields['home_team'].queryset = qs
        self.fields['away_team'].queryset = qs


class SubstitutionForm(forms.ModelForm):
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        if team:
            self.fields['player_in'].queryset = Players.objects.filter(team_serial=team)
            self.fields['player_out'].queryset = Players.objects.filter(team_serial=team)

    class Meta:
        model = Substitution
        fields = ['player_in', 'player_out', 'inning', 'position']
        widgets = {
            'inning': forms.NumberInput(attrs={'class': 'form-control'}),
            'position': forms.Select(choices=POSITIONS, attrs={'class': 'form-control'}),
        }

class InningScoreForm(forms.ModelForm):
    class Meta:
        model = InningScore
        fields = ['inning', 'runs']
        widgets = {
            'inning': forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 60px;'}),
            'runs': forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 60px;'}),
        }

# Create the formset—no extra blank rows, and no delete checkbox
InningScoreFormSet = modelformset_factory(
    InningScore,
    form=InningScoreForm,
    extra=0,
    can_delete=False
)

class OffenseForm(forms.Form):
    ab      = forms.IntegerField(min_value=0, required=False, initial=0, label="AB")
    r       = forms.IntegerField(min_value=0, required=False, initial=0, label="R")
    h       = forms.IntegerField(min_value=0, required=False, initial=0, label="H")
    doubles = forms.IntegerField(min_value=0, required=False, initial=0, label="2B")
    triples = forms.IntegerField(min_value=0, required=False, initial=0, label="3B")
    hr      = forms.IntegerField(min_value=0, required=False, initial=0, label="HR")
    rbi     = forms.IntegerField(min_value=0, required=False, initial=0, label="RBI")
    so      = forms.IntegerField(min_value=0, required=False, initial=0, label="SO")
    bb      = forms.IntegerField(min_value=0, required=False, initial=0, label="BB")
    sf      = forms.IntegerField(min_value=0, required=False, initial=0, label="SF")
    sb      = forms.IntegerField(min_value=0, required=False, initial=0, label="SB")
    cs      = forms.IntegerField(min_value=0, required=False, initial=0, label="CS")
    hbp     = forms.IntegerField(min_value=0, required=False, initial=0, label="HBP")
    dp      = forms.IntegerField(min_value=0, required=False, initial=0, label="DP")

class DefenseForm(forms.Form):
    po      = forms.IntegerField(min_value=0, required=False, initial=0, label="PO")
    a       = forms.IntegerField(min_value=0, required=False, initial=0, label="A")
    e       = forms.IntegerField(min_value=0, required=False, initial=0, label="E")
    # catcher‐only
    sb      = forms.IntegerField(min_value=0, required=False, initial=0, label="SB")
    cs      = forms.IntegerField(min_value=0, required=False, initial=0, label="CS")
    pb      = forms.IntegerField(min_value=0, required=False, initial=0, label="PB")

class PitchingForm(forms.Form):
    ip_outs     = forms.CharField(
                    required=False,
                    initial="0.0",
                    label="IP",
                    help_text="e.g. 6.2 for 6⅔ innings"
                  )
    ra          = forms.CharField(
                    required=False,
                    initial="0",
                    label="R",
                    help_text="Runs Allowed"
                  )
    er          = forms.IntegerField(min_value=0, required=False, initial=0, label="ER")
    h_allowed   = forms.IntegerField(min_value=0, required=False, initial=0, label="Hits Allowed")
    hra         = forms.IntegerField(min_value=0, required=False, initial=0, label="HRA")
    k_thrown    = forms.IntegerField(min_value=0, required=False, initial=0, label="K")
    bb_allowed  = forms.IntegerField(min_value=0, required=False, initial=0, label="BB")
    decision    = forms.ChoiceField(
                     choices=[('','None'),('W','Win'),('L','Loss'),('S','Save')],
                     required=False,
                     label="Decision"
                  )
    balk        = forms.IntegerField(min_value=0, required=False, initial=0, label="Balk")
    wp          = forms.IntegerField(min_value=0, required=False, initial=0, label="WP")
    ibb         = forms.IntegerField(min_value=0, required=False, initial=0, label="IBB")

    def clean_ip_outs(self):
        raw = (self.cleaned_data.get('ip_outs') or '').strip()
        if not raw:
            return 0
        if raw.startswith('.'):
            raw = '0' + raw
        try:
            if '.' in raw:
                full_str, part_str = raw.split('.')
                full, part = int(full_str), int(part_str)
            else:
                full, part = int(raw), 0
            if part not in (0, 1, 2):
                raise ValueError
            # convert to total outs
            return full * 3 + part
        except ValueError:
            raise forms.ValidationError(
                "Use baseball format for IP: e.g., 5.2 (5 innings, 2 outs)"
            )

    def clean_ra(self):
        raw = (self.cleaned_data.get('ra') or '').strip()
        if not raw:
            return 0
        try:
            return int(raw)
        except ValueError:
            raise forms.ValidationError("Runs Allowed must be a whole number.")


class CompetitionSelectForm(forms.Form):
    competitions = forms.ModelMultipleChoiceField(
        queryset=Competition.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Choose one or more competitions",
    )

class TeamEntryForm(forms.ModelForm):
    class Meta:
        model = TeamEntry
        fields = ['team']
        widgets = {
            'team': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'team': 'Select Team',
        }