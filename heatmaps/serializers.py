from rest_framework import serializers

from heatmaps.models import CellResult, ComputationResult, Scenario, TargetPoint


class TargetPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetPoint
        fields = ("id", "name", "lat", "lng", "weight")


class ScenarioSerializer(serializers.ModelSerializer):
    targets = TargetPointSerializer(many=True)

    class Meta:
        model = Scenario
        fields = (
            "id",
            "name",
            "creator",
            "created_at",
            "polygon_geojson",
            "metric",
            "mode",
            "departure_time",
            "grid_resolution_m",
            "targets",
        )
        read_only_fields = ("creator", "created_at")

    def create(self, validated_data):
        targets_data = validated_data.pop("targets", [])
        scenario = Scenario.objects.create(**validated_data)
        for target in targets_data:
            TargetPoint.objects.create(scenario=scenario, **target)
        ComputationResult.objects.create(
            scenario=scenario, status=ComputationResult.STATUS_PENDING
        )
        return scenario


class ComputationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComputationResult
        fields = (
            "status",
            "started_at",
            "finished_at",
            "num_cells",
            "error_message",
        )


class ScenarioDetailSerializer(serializers.ModelSerializer):
    targets = TargetPointSerializer(many=True)
    computation = ComputationResultSerializer()

    class Meta:
        model = Scenario
        fields = (
            "id",
            "name",
            "creator",
            "created_at",
            "polygon_geojson",
            "metric",
            "mode",
            "departure_time",
            "grid_resolution_m",
            "targets",
            "computation",
        )


class CellResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = CellResult
        fields = ("lat", "lng", "time_minutes")
