from django import forms
from django.forms import modelformset_factory
from .models import (
    Competition, Game, LineupEntry, PlayerStatLine,
    Substitution, InningScore
)
from players.models import Players

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
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class GameForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['competition', 'date_played', 'home_team', 'away_team', 'home_score', 'away_score']
        widgets = {
            'competition': forms.Select(attrs={'class': 'form-control'}),
            'date_played': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'home_team': forms.Select(attrs={'class': 'form-control'}),
            'away_team': forms.Select(attrs={'class': 'form-control'}),
            'home_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'away_score': forms.NumberInput(attrs={'class': 'form-control'}),
        }

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


class BattingStatForm(forms.ModelForm):
    class Meta:
        model = PlayerStatLine
        fields = [
            'ab',       # At‐bats
            'h',        # Hits
            'doubles',  # Doubles
            'triples',  # Triples
            'hr',       # Home runs
            'r',        # Runs
            'rbi',      # RBI
            'bb',       # Walks
            'so',       # Strikeouts
            'sf',       # Sac flies
            'hbp',      # Hit by pitch
            'sb',       # Stolen bases
            'cs',       # Caught stealing
            'dp',       # Double plays
        ]
        widgets = {
            name: forms.NumberInput(
                attrs={'class': 'form-control', 'style': 'width: 80px;'}
            )
            for name in fields
        }


class PitchDefStatForm(forms.ModelForm):
    # override the model’s IntegerFields with CharFields…
    ip_outs = forms.CharField(
        label="IP",
        required=False,
        widget=forms.TextInput(attrs={'class':'form-control','style':'width:80px;'})
    )
    ra = forms.CharField(
        label="Runs Allowed",
        required=False,
        widget=forms.NumberInput(attrs={'class':'form-control','style':'width:80px;'})
    )

    class Meta:
        model = PlayerStatLine
        fields = [
            'ip_outs', 'ra', 'er', 'h_allowed', 'hra', 'k_thrown', 'bb_allowed',
            'decision', 'balk', 'hb', 'wp', 'ibb',
            'po', 'a', 'e', 'pb'
        ]
        widgets = {
            # If you want custom widgets for the others, list them here
        }

    def clean_ip_outs(self):
        raw = (self.cleaned_data.get('ip_outs') or '').strip()
        if raw == '':
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
            return full * 3 + part
        except ValueError:
            raise forms.ValidationError(
                "Use baseball format for IP: e.g., 5.2 (5 innings, 2 outs)"
            )

    def clean_ra(self):
        raw = (self.cleaned_data.get('ra') or '').strip()
        if raw == '':
            return 0
        try:
            return int(raw)
        except ValueError:
            raise forms.ValidationError("Runs Allowed must be a whole number.")


# Formset factories
BattingStatFormSet = modelformset_factory(
    PlayerStatLine,
    form=BattingStatForm,
    extra=0,
    can_delete=False
)

PitchDefStatFormSet = modelformset_factory(
    PlayerStatLine,
    form=PitchDefStatForm,
    extra=0,
    can_delete=False
)

class CompetitionSelectForm(forms.Form):
    competitions = forms.ModelMultipleChoiceField(
        queryset=Competition.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Choose one or more competitions",
    )
