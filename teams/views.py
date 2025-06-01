from django.shortcuts import render

def create_team(request):
    return render(request, 'teams/create_team.html')

def view_team(request):
    return render(request, 'teams/view_team.html')

def edit_team(request):
    return render(request, 'teams/edit_team.html')
