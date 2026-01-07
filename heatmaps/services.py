import datetime as dt
import os
from dataclasses import dataclass
from typing import Iterable, List, Optional

import requests
from pyproj import Transformer
from shapely.geometry import Point, shape

from heatmaps.models import Scenario, TargetPoint


@dataclass
class Cell:
    lat: float
    lng: float


class GoogleDirectionsClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")

    def get_transit_duration_seconds(
        self,
        origin: Cell,
        destination: TargetPoint,
        departure_time: Optional[dt.datetime] = None,
        mode: str = "transit",
    ) -> Optional[int]:
        if not self.api_key:
            return None
        params = {
            "origin": f"{origin.lat},{origin.lng}",
            "destination": f"{destination.lat},{destination.lng}",
            "mode": mode,
            "key": self.api_key,
        }
        if departure_time:
            params["departure_time"] = int(departure_time.timestamp())
        response = requests.get(
            "https://maps.googleapis.com/maps/api/directions/json", params=params, timeout=20
        )
        payload = response.json()
        if payload.get("status") != "OK":
            return None
        try:
            return payload["routes"][0]["legs"][0]["duration"]["value"]
        except (KeyError, IndexError, TypeError):
            return None


class GridGenerator:
    def __init__(self) -> None:
        self._to_mercator = Transformer.from_crs(4326, 3857, always_xy=True)
        self._to_wgs = Transformer.from_crs(3857, 4326, always_xy=True)

    def generate_grid(self, polygon_geojson: dict, resolution_m: int) -> List[Cell]:
        polygon = shape(polygon_geojson)
        projected = self._project_geometry(polygon)
        minx, miny, maxx, maxy = projected.bounds
        cells: List[Cell] = []
        x = minx
        while x <= maxx:
            y = miny
            while y <= maxy:
                point = Point(x, y)
                if projected.contains(point):
                    lng, lat = self._to_wgs.transform(x, y)
                    cells.append(Cell(lat=lat, lng=lng))
                y += resolution_m
            x += resolution_m
        return cells

    def _project_geometry(self, polygon):
        coords = [self._to_mercator.transform(*coord) for coord in polygon.exterior.coords]
        return type(polygon)(coords)


def aggregate_durations(
    durations: Iterable[Optional[int]],
    targets: Iterable[TargetPoint],
    metric: str,
) -> Optional[float]:
    valid: List[int] = [value for value in durations if value is not None]
    if not valid:
        return None
    if metric == Scenario.METRIC_MIN:
        return min(valid) / 60
    if metric == Scenario.METRIC_AVG:
        return sum(valid) / len(valid) / 60
    if metric == Scenario.METRIC_WEIGHTED:
        weighted_sum = 0.0
        total_weight = 0.0
        for duration, target in zip(durations, targets):
            if duration is None:
                continue
            weight = target.weight or 1.0
            weighted_sum += duration * weight
            total_weight += weight
        if total_weight == 0:
            return None
        return weighted_sum / total_weight / 60
    return min(valid) / 60


def compute_times(
    cells: Iterable[Cell],
    targets: Iterable[TargetPoint],
    departure_time: Optional[dt.datetime],
    metric: str,
    mode: str = "transit",
    client: Optional[GoogleDirectionsClient] = None,
) -> List[dict]:
    client = client or GoogleDirectionsClient()
    results = []
    targets_list = list(targets)
    for cell in cells:
        durations = [
            client.get_transit_duration_seconds(cell, target, departure_time, mode)
            for target in targets_list
        ]
        time_minutes = aggregate_durations(durations, targets_list, metric)
        results.append(
            {
                "lat": cell.lat,
                "lng": cell.lng,
                "time_minutes": time_minutes,
                "raw": {"durations": durations},
            }
        )
    return results
