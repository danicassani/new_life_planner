from django.conf import settings
from django.db import models


class Scenario(models.Model):
    METRIC_MIN = "MIN"
    METRIC_AVG = "AVG"
    METRIC_WEIGHTED = "WEIGHTED_AVG"
    METRIC_CHOICES = [
        (METRIC_MIN, "Min"),
        (METRIC_AVG, "Average"),
        (METRIC_WEIGHTED, "Weighted average"),
    ]

    name = models.CharField(max_length=255)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scenarios",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    polygon_geojson = models.JSONField()
    metric = models.CharField(max_length=20, choices=METRIC_CHOICES, default=METRIC_MIN)
    mode = models.CharField(max_length=20, default="transit")
    departure_time = models.DateTimeField(null=True, blank=True)
    grid_resolution_m = models.PositiveIntegerField(default=500)

    def __str__(self) -> str:
        return self.name


class TargetPoint(models.Model):
    scenario = models.ForeignKey(
        Scenario, on_delete=models.CASCADE, related_name="targets"
    )
    name = models.CharField(max_length=255)
    lat = models.FloatField()
    lng = models.FloatField()
    weight = models.FloatField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.lat}, {self.lng})"


class ComputationResult(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_RUNNING = "RUNNING"
    STATUS_DONE = "DONE"
    STATUS_ERROR = "ERROR"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_DONE, "Done"),
        (STATUS_ERROR, "Error"),
    ]

    scenario = models.OneToOneField(
        Scenario, on_delete=models.CASCADE, related_name="computation"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    num_cells = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.scenario.name} ({self.status})"


class CellResult(models.Model):
    scenario = models.ForeignKey(
        Scenario, on_delete=models.CASCADE, related_name="cell_results"
    )
    lat = models.FloatField()
    lng = models.FloatField()
    time_minutes = models.FloatField(null=True, blank=True)
    raw = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ("scenario", "lat", "lng")

    def __str__(self) -> str:
        return f"{self.scenario.name} ({self.lat}, {self.lng})"
