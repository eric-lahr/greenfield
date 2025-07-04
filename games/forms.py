from django import forms
from stats.models import Game

class GameSetupForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = [
            'competition', 'date_played',
            'home_team', 'away_team',
            'venue', 'weather',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }
