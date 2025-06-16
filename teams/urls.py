from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_team, name='create'),
    path('teams/view_team/', views.new_view_team, name='new_view_team'),
    path('edit/', views.edit_team, name='edit'),
    path('teams/view_team/pdf/<int:team_serial>/', views.new_create_pdf, name='new_create_pdf'),
]