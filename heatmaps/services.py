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
            raise RuntimeError("Missing GOOGLE_MAPS_API_KEY for Google Routes API.")
        if mode == "transit" and not departure_time:
            departure_time = dt.datetime.now(tz=dt.timezone.utc)
        payload = {
            "origin": {"location": {"latLng": {"latitude": origin.lat, "longitude": origin.lng}}},
            "destination": {
                "location": {
                    "latLng": {"latitude": destination.lat, "longitude": destination.lng}
                }
            },
            "travelMode": mode.upper(),
        }
        if departure_time:
            payload["departureTime"] = departure_time.isoformat()
        response = requests.post(
            "https://routes.googleapis.com/directions/v2:computeRoutes",
            headers={
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "routes.duration",
            },
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if "routes" not in data or not data["routes"]:
            print(
                "Google Routes error for "
                f"({origin.lat}, {origin.lng}) -> ({destination.lat}, {destination.lng}): "
                f"{data.get('error', {}).get('message', 'No routes returned')}"
            )
            return None
        try:
            return _parse_duration_seconds(data["routes"][0]["duration"])
        except (KeyError, IndexError, TypeError):
            return None


def _parse_duration_seconds(duration_value: str) -> Optional[int]:
    if not duration_value:
        return None
    if isinstance(duration_value, str) and duration_value.endswith("s"):
        return int(float(duration_value[:-1]))
    if isinstance(duration_value, (int, float)):
        return int(duration_value)
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
        print(
            f"Computed durations for cell ({cell.lat}, {cell.lng}): {durations}"
        )
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
