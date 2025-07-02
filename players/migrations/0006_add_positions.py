from django.db import migrations

def populate_positions(apps, schema_editor):
    Position = apps.get_model('players', 'Position')  # Use the historical model
    position_names = ['P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'OF', 'DH']

    for name in position_names:
        Position.objects.create(name=name)

class Migration(migrations.Migration):

    dependencies = [
        ('players', '0005_position_remove_players_defense_1_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_positions),
    ]

