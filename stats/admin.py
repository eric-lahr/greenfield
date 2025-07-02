from django.contrib import admin
from .models import *

admin.site.register(Competition)
admin.site.register(League)
admin.site.register(Division)
admin.site.register(Game)
admin.site.register(TeamStanding)
admin.site.register(PlayerStatLine)
admin.site.register(LineupEntry)
admin.site.register(Substitution)
admin.site.register(InningScore)