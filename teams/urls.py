from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_team, name='create'),
    path('teams/view_team/', views.new_view_team, name='new_view_team'),
    path('edit/', views.edit_team, name='edit'),
    path('teams/view_team/pdf/<int:team_serial>/', views.new_create_pdf, name='new_create_pdf'),
    path('teams/<int:team_serial>/pdf_batters/', views.create_pdf_batters, name='create_pdf_batters'),
    path('teams/<int:team_serial>/pdf_pitchers/', views.create_pdf_pitchers, name='create_pdf_pitchers'),
    path('teams/<int:team_serial>/csv_batters/', views.create_csv_batters, name='create_csv_batters'),
    path('teams/<int:team_serial>/csv_pitchers/', views.create_csv_pitchers, name='create_csv_pitchers'),
]