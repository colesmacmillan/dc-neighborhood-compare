from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import osmnx as ox


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "neighborhoods.json"
DEFAULT_RADIUS_M = 1200


NEIGHBORHOODS = [
    {
        "name": "NoMa",
        "lat": 38.9066,
        "lon": -77.0033,
        "radius_m": DEFAULT_RADIUS_M,
        "summary": "Fast-growing, apartment-heavy neighborhood with strong Metro access and plenty of casual food options.",
        "rent_1br": 2650,
    },
    {
        "name": "Navy Yard",
        "lat": 38.8765,
        "lon": -77.0059,
        "radius_m": DEFAULT_RADIUS_M,
        "summary": "Modern waterfront area with newer buildings, Nationals Park energy, and an easy social scene.",
        "rent_1br": 2925,
    },
    {
        "name": "U Street",
        "lat": 38.9160,
        "lon": -77.0280,
        "radius_m": DEFAULT_RADIUS_M,
        "summary": "Dense, lively, and walkable with a strong restaurant and nightlife cluster popular with recent grads.",
        "rent_1br": 2550,
    },
    {
        "name": "Dupont Circle",
        "lat": 38.9096,
        "lon": -77.0434,
        "radius_m": DEFAULT_RADIUS_M,
        "summary": "Central, polished, and highly walkable with a mix of restaurants, offices, and classic DC apartment stock.",
        "rent_1br": 3050,
    },
    {
        "name": "Georgetown",
        "lat": 38.9076,
        "lon": -77.0723,
        "radius_m": DEFAULT_RADIUS_M,
        "summary": "Historic and polished with strong retail and dining, fewer Metro connections, and some of the highest rents.",
        "rent_1br": 3300,
    },
]


METRIC_TAGS = {
    "food_density": {
        "amenity": [
            "restaurant",
            "fast_food",
            "cafe",
            "bar",
            "pub",
            "food_court",
            "biergarten",
        ]
    },
    "nightlife_density": {"amenity": ["bar", "pub", "nightclub"]},
    "grocery_density": {"shop": ["supermarket", "convenience"]},
    "green_density": {"leisure": ["park", "garden"]},
    "transit_density": {
        "public_transport": True,
        "railway": ["station", "subway_entrance", "halt", "tram_stop"],
        "station": ["subway"],
        "amenity": ["bus_station"],
    },
}


def fetch_feature_count(lat: float, lon: float, radius_m: int, tags: dict[str, Any]) -> int:
    features = ox.features_from_point((lat, lon), tags=tags, dist=radius_m)
    if features.empty:
        return 0
    return int(features.index.nunique())


def density_from_count(count: int, radius_m: int) -> float:
    area_sq_km = math.pi * (radius_m**2) / 1_000_000
    return round(count / area_sq_km, 1)


def build_record(neighborhood: dict[str, Any]) -> dict[str, Any]:
    metrics = {}
    for metric_name, tags in METRIC_TAGS.items():
        count = fetch_feature_count(
            neighborhood["lat"],
            neighborhood["lon"],
            neighborhood["radius_m"],
            tags,
        )
        metrics[metric_name] = density_from_count(count, neighborhood["radius_m"])

    return {
        "name": neighborhood["name"],
        "lat": neighborhood["lat"],
        "lon": neighborhood["lon"],
        "radius_m": neighborhood["radius_m"],
        "summary": neighborhood["summary"],
        "rent_1br": neighborhood["rent_1br"],
        "metrics": metrics,
    }


def main() -> None:
    ox.settings.use_cache = True
    ox.settings.log_console = True

    records = [build_record(neighborhood) for neighborhood in NEIGHBORHOODS]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} neighborhoods to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
