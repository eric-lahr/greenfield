from django import forms
from .models import Competition, Game, LineupEntry
from players.models import Players

POSITIONS = [
    ("P", "P"), ("C", "C"), ("1B", "1B"), ("2B", "2B"), ("3B", "3B"),
    ("SS", "SS"), ("LF", "LF"), ("CF", "CF"), ("RF", "RF"), ("DH", "DH"),
]

class LineupEntryForm(forms.Form):
    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)

        if team:
            players = Players.objects.filter(team_serial=team)
        else:
            players = Players.objects.none()

        for i in range(1, 10):
            self.fields[f'player_{i}'] = forms.ModelChoiceField(
                queryset=players,
                label=f"Batting #{i}",
                required=True,
                widget=forms.Select(attrs={'class': 'form-control'})
            )
            self.fields[f'position_{i}'] = forms.ChoiceField(
                choices=POSITIONS,
                label=f"Position #{i}",
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