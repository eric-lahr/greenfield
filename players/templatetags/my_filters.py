from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')

@register.filter
def get_team_name(teams, team_id):
    team = teams.filter(pk=team_id).first()
    return f"{team.first_name} {team.team_name}" if team else "Unknown Team"