from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory, BaseInlineFormSet
from .models import Lineup, TeamLineupEntry

class LineupForm(forms.ModelForm):
    class Meta:
        model = Lineup
        fields = ['name','description','allow_dh']

class BaseLineupEntryFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        positions = set()
        orders    = set()
        for form in self.forms:
            if form.cleaned_data.get('DELETE') or not form.cleaned_data:
                continue

            pos   = form.cleaned_data['field_position']
            order = form.cleaned_data['batting_order']

            if pos in positions:
                raise ValidationError("You can’t repeat a position in the same lineup.")
            positions.add(pos)

            if order in orders:
                raise ValidationError("You can’t repeat a batting order slot.")
            orders.add(order)

        # enforce exact number of slots
        expected = 9 if self.instance.allow_dh else 8
        if len(orders) != expected:
            raise ValidationError(f"This lineup must have exactly {expected} players (you have {len(orders)}).")

LineupEntryFormSet = inlineformset_factory(
    Lineup, TeamLineupEntry,
    formset=BaseLineupEntryFormSet,
    fields=['player','batting_order','field_position'],
    extra=9,      # will be overridden dynamically
    max_num=9,
    can_delete=True,
)
