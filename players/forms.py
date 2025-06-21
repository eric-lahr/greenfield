from django import forms
from .models import Players, PlayerPositionRating, Position
from django.forms import formset_factory, modelformset_factory

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

PlayerPositionRatingModelFormset = modelformset_factory(
    PlayerPositionRating,
    form=PlayerPositionRatingForm,
    extra=0,
    can_delete=True
)

class PlayerEditForm(forms.ModelForm):
    class Meta:
        model = Players
        fields = [
            'year', 'first_name', 'last_name', 'bats', 'throws', 'uni_num',
            'offense', 'bat_prob_hit', 'pitching', 'pitch_ctl', 'pitch_prob_hit', 'team_serial'
        ]

class CustomPlayerStatsForm(forms.Form):
    # Identity
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    year = forms.CharField(max_length=10)
    team_name = forms.CharField(max_length=100)

    bats = forms.ChoiceField(choices=[('R', 'Right'), ('L', 'Left'), ('S', 'Switch')])
    throws = forms.ChoiceField(choices=[('R', 'Right'), ('L', 'Left')])

    # Batting
    G = forms.IntegerField()
    H = forms.IntegerField()
    AB = forms.IntegerField()
    HR = forms.IntegerField()
    doubles = forms.IntegerField()
    triples = forms.IntegerField()
    BB = forms.IntegerField()
    HBP = forms.IntegerField()
    SB = forms.IntegerField()
    RBI = forms.IntegerField()
    SO = forms.IntegerField()
    SF = forms.IntegerField(required=False)
    SH = forms.IntegerField(required=False)

    # Pitching
    BFP = forms.IntegerField(required=False)
    HA = forms.IntegerField(required=False)
    BB_pitch = forms.IntegerField(required=False)
    HBP_pitch = forms.IntegerField(required=False)
    BAOpp = forms.FloatField(required=False)
    GP = forms.IntegerField(required=False)
    IP_outs = forms.IntegerField(required=False)
    SO_pitch = forms.IntegerField(required=False)
    HRA = forms.IntegerField(required=False)
    WP = forms.IntegerField(required=False)

    # Fielding (up to 6 positions)
    POS1 = forms.CharField(required=False)
    POS1_PO = forms.IntegerField(required=False)
    POS1_A = forms.IntegerField(required=False)
    POS1_E = forms.IntegerField(required=False)
    POS1_G = forms.IntegerField(required=False)

    POS2 = forms.CharField(required=False)
    POS2_PO = forms.IntegerField(required=False)
    POS2_A = forms.IntegerField(required=False)
    POS2_E = forms.IntegerField(required=False)
    POS2_G = forms.IntegerField(required=False)

    POS3 = forms.CharField(required=False)
    POS3_PO = forms.IntegerField(required=False)
    POS3_A = forms.IntegerField(required=False)
    POS3_E = forms.IntegerField(required=False)
    POS3_G = forms.IntegerField(required=False)

    POS4 = forms.CharField(required=False)
    POS4_PO = forms.IntegerField(required=False)
    POS4_A = forms.IntegerField(required=False)
    POS4_E = forms.IntegerField(required=False)
    POS4_G = forms.IntegerField(required=False)

    POS5 = forms.CharField(required=False)
    POS5_PO = forms.IntegerField(required=False)
    POS5_A = forms.IntegerField(required=False)
    POS5_E = forms.IntegerField(required=False)
    POS5_G = forms.IntegerField(required=False)

    # Optional: add CS/SBA if POS is catcher
    CS = forms.IntegerField(required=False)
    SBA = forms.IntegerField(required=False)