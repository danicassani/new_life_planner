import os

from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from heatmaps.models import CellResult, ComputationResult, Scenario
from heatmaps.serializers import (
    CellResultSerializer,
    ScenarioDetailSerializer,
    ScenarioSerializer,
)
from heatmaps.services import GridGenerator, compute_times


def index(request):
    context = {"google_maps_api_key": os.getenv("GOOGLE_MAPS_API_KEY", "")}
    return render(request, "heatmaps/index.html", context)


class ScenarioListCreateView(APIView):
    def post(self, request):
        serializer = ScenarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scenario = serializer.save(creator=request.user if request.user.is_authenticated else None)
        return Response(ScenarioDetailSerializer(scenario).data, status=status.HTTP_201_CREATED)


class ScenarioDetailView(APIView):
    def get(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id)
        return Response(ScenarioDetailSerializer(scenario).data)


class ScenarioRunView(APIView):
    def post(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id)
        computation = scenario.computation
        computation.status = ComputationResult.STATUS_RUNNING
        computation.started_at = timezone.now()
        computation.error_message = ""
        computation.save(update_fields=["status", "started_at", "error_message"])

        try:
            grid = GridGenerator().generate_grid(
                scenario.polygon_geojson, scenario.grid_resolution_m
            )
            results = compute_times(
                grid,
                scenario.targets.all(),
                scenario.departure_time,
                scenario.metric,
                scenario.mode,
            )
            CellResult.objects.filter(scenario=scenario).delete()
            CellResult.objects.bulk_create(
                [
                    CellResult(
                        scenario=scenario,
                        lat=result["lat"],
                        lng=result["lng"],
                        time_minutes=result["time_minutes"],
                        raw=result["raw"],
                    )
                    for result in results
                ]
            )
            computation.status = ComputationResult.STATUS_DONE
            computation.finished_at = timezone.now()
            computation.num_cells = len(results)
            computation.save(
                update_fields=["status", "finished_at", "num_cells"]
            )
        except Exception as exc:  # noqa: BLE001
            computation.status = ComputationResult.STATUS_ERROR
            computation.finished_at = timezone.now()
            computation.error_message = str(exc)
            computation.save(
                update_fields=["status", "finished_at", "error_message"]
            )
            return Response(
                {"detail": "Error while computing heatmap.", "error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"detail": "Computation finished."})


class ScenarioResultsView(APIView):
    def get(self, request, scenario_id):
        scenario = get_object_or_404(Scenario, pk=scenario_id)
        results = scenario.cell_results.all()
        serializer = CellResultSerializer(results, many=True)
        feature_collection = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [item["lng"], item["lat"]],
                    },
                    "properties": {"time_minutes": item["time_minutes"]},
                }
                for item in serializer.data
            ],
        }
        return Response(feature_collection)
