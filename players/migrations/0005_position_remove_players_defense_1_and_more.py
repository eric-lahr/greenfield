# Generated by Django 5.2.1 on 2025-06-05 14:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("players", "0004_rename_defense_players_defense_1_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Position",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=3, unique=True)),
            ],
        ),
        migrations.RemoveField(
            model_name="players",
            name="defense_1",
        ),
        migrations.RemoveField(
            model_name="players",
            name="defense_2",
        ),
        migrations.RemoveField(
            model_name="players",
            name="defense_3",
        ),
        migrations.RemoveField(
            model_name="players",
            name="defense_4",
        ),
        migrations.RemoveField(
            model_name="players",
            name="defense_5",
        ),
        migrations.RemoveField(
            model_name="players",
            name="defense_6",
        ),
        migrations.RemoveField(
            model_name="players",
            name="defense_7",
        ),
        migrations.RemoveField(
            model_name="players",
            name="defense_8",
        ),
        migrations.RemoveField(
            model_name="players",
            name="defense_9",
        ),
        migrations.RemoveField(
            model_name="players",
            name="position_1",
        ),
        migrations.RemoveField(
            model_name="players",
            name="position_2",
        ),
        migrations.RemoveField(
            model_name="players",
            name="position_3",
        ),
        migrations.RemoveField(
            model_name="players",
            name="position_4",
        ),
        migrations.RemoveField(
            model_name="players",
            name="position_5",
        ),
        migrations.RemoveField(
            model_name="players",
            name="position_6",
        ),
        migrations.RemoveField(
            model_name="players",
            name="position_7",
        ),
        migrations.RemoveField(
            model_name="players",
            name="position_8",
        ),
        migrations.RemoveField(
            model_name="players",
            name="position_9",
        ),
        migrations.CreateModel(
            name="PlayerPositionRating",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("rating", models.CharField(max_length=10)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="position_ratings",
                        to="players.players",
                    ),
                ),
                (
                    "position",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="players.position",
                    ),
                ),
            ],
            options={
                "unique_together": {("player", "position")},
            },
        ),
    ]
