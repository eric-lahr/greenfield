from django import forms
from .models import Players, PlayerPositionRating, Position
from django.forms import formset_factory

class PlayerForm(forms.ModelForm):
    class Meta:
        model = Players
        fields = [
            'bats', 'throws', 'uni_num', 'offense',
            'bat_prob_hit', 'pitching', 'pitch_ctl', 'pitch_prob_hit'
        ]

class PlayerPositionRatingForm(forms.ModelForm):
    class Meta:
        model = PlayerPositionRating
        fields = ['position', 'rating']

PlayerPositionRatingFormSet = formset_factory(
    PlayerPositionRatingForm,
    extra=0,
    can_delete=True
)
