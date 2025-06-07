from django import template
from ..models import Teams

register = template.Library()

@register.filter
def get_team_name(teams, selected_id):
    try:
        team = teams.get(id=selected_id)
        return f"{team.first_name} {team.team_name}"
    except Teams.DoesNotExist:
        return "Unknown Team"

@register.filter
def get(dict_data, key):
    return dict_data.get(key)