# teams/urls.py

from django.urls import path
from . import views

app_name = 'teams'

urlpatterns = [
    # — Create / menu-driven view/edit (uses ?team_id=…)
    path('create/', views.create_team,      name='create'),
    path('view_team/', views.new_view_team, name='new_view_team'),
    path('edit/',      views.edit_team,     name='edit'),

    # — PDFs & CSVs (pass team_serial into the view)
    path('view_team/pdf/<int:team_serial>/',     views.new_create_pdf,      name='new_create_pdf'),
    path('<int:team_serial>/pdf/batters/',       views.create_pdf_batters,  name='create_pdf_batters'),
    path('<int:team_serial>/pdf/pitchers/',      views.create_pdf_pitchers, name='create_pdf_pitchers'),
    path('<int:team_serial>/csv/batters/',       views.create_csv_batters,  name='create_csv_batters'),
    path('<int:team_serial>/csv/pitchers/',      views.create_csv_pitchers, name='create_csv_pitchers'),

    # — Manage Lineups (now matches manage_lineup(request, team_id, …) signature)
    path('<int:team_id>/lineups/',               views.manage_lineup,       name='manage_lineup'),
    path('<int:team_id>/lineups/<int:lineup_id>/', views.manage_lineup,       name='edit_lineup'),
]
