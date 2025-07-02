from django.contrib import admin
from .models import Players, PlayerPositionRating, Position, PlayerPicture

@admin.register(Players)
class PlayersAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'year', 'team_serial')
    list_filter = ('team_serial',)  # 👈 Enables filtering by team in the sidebar

# Optionally register the other models too
admin.site.register(PlayerPositionRating)
admin.site.register(Position)
admin.site.register(PlayerPicture)

