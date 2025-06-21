from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')

@register.filter
def get_team_name(game, team_label):
    if team_label == 'home':
        team = game.home_team
    elif team_label == 'away':
        team = game.away_team
    else:
        return "Unknown Team"

    return f"{team.first_name} {team.team_name}" if team else "Unknown Team"

@register.filter
def to(start, end):
    return range(start, end)

@register.filter
def outs_to_ip(outs):
    try:
        outs = int(outs)
        return f"{outs // 3}.{outs % 3}"
    except:
        return ''