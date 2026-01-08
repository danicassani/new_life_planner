from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Scenario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("polygon_geojson", models.JSONField()),
                (
                    "metric",
                    models.CharField(
                        choices=[("MIN", "Min"), ("AVG", "Average"), ("WEIGHTED_AVG", "Weighted average")],
                        default="MIN",
                        max_length=20,
                    ),
                ),
                ("mode", models.CharField(default="transit", max_length=20)),
                ("departure_time", models.DateTimeField(blank=True, null=True)),
                ("grid_resolution_m", models.PositiveIntegerField(default=500)),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scenarios",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TargetPoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("lat", models.FloatField()),
                ("lng", models.FloatField()),
                ("weight", models.FloatField(blank=True, null=True)),
                (
                    "scenario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="targets",
                        to="heatmaps.scenario",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ComputationResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("RUNNING", "Running"),
                            ("DONE", "Done"),
                            ("ERROR", "Error"),
                        ],
                        max_length=20,
                    ),
                ),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("num_cells", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                (
                    "scenario",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="computation",
                        to="heatmaps.scenario",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CellResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lat", models.FloatField()),
                ("lng", models.FloatField()),
                ("time_minutes", models.FloatField(blank=True, null=True)),
                ("raw", models.JSONField(blank=True, null=True)),
                (
                    "scenario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cell_results",
                        to="heatmaps.scenario",
                    ),
                ),
            ],
            options={
                "unique_together": {("scenario", "lat", "lng")},
            },
        ),
    ]
