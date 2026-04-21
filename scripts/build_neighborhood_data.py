from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import osmnx as ox
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "neighborhoods.json"
DEFAULT_RADIUS_M = 1200


NEIGHBORHOODS = [
    {
        "name": "Navy Yard",
        "lat": 38.8765,
        "lon": -77.0059,
        "radius_m": DEFAULT_RADIUS_M,
        "summary": "Modern waterfront area with newer buildings, a lively restaurant scene, and strong appeal for young professionals.",
        "rent_1br": 2925,
        "rent_2br": 4625,
        "rent_3br": 6180,
        "rent_proxy": {"kind": "zip", "region": "20003", "state": "DC"},
    },
    {
        "name": "NoMa",
        "lat": 38.9066,
        "lon": -77.0033,
        "radius_m": DEFAULT_RADIUS_M,
        "summary": "Fast-growing and apartment-heavy with strong Metro access, coworking energy, and lots of casual food options.",
        "rent_1br": 2650,
        "rent_2br": 4225,
        "rent_3br": 5640,
        "rent_proxy": {"kind": "zip", "region": "20002", "state": "DC"},
    },
    {
        "name": "Foggy Bottom",
        "lat": 38.9007,
        "lon": -77.0502,
        "radius_m": DEFAULT_RADIUS_M,
        "summary": "Central and practical with easy downtown access, Metro convenience, and a quieter feel than the nightlife-heavy areas.",
        "rent_1br": 2875,
        "rent_2br": 4510,
        "rent_3br": 5970,
        "rent_proxy": {"kind": "zip", "region": "20037", "state": "DC"},
    },
    {
        "name": "Adams Morgan",
        "lat": 38.9227,
        "lon": -77.0424,
        "radius_m": DEFAULT_RADIUS_M,
        "summary": "Social, energetic, and nightlife-focused with dense dining options and a strong weekend scene.",
        "rent_1br": 2475,
        "rent_2br": 3940,
        "rent_3br": 5310,
        "rent_proxy": {"kind": "zip", "region": "20009", "state": "DC"},
    },
    {
        "name": "Arlington",
        "lat": 38.8816,
        "lon": -77.0910,
        "radius_m": 1400,
        "summary": "Clean, structured, and consistently popular with post-grad professionals who want convenience and a slightly calmer feel.",
        "rent_1br": 2525,
        "rent_2br": 4040,
        "rent_3br": 5460,
        "rent_proxy": {"kind": "county", "region": "Arlington County", "state": "VA"},
    },
    {
        "name": "Ballston",
        "lat": 38.8814,
        "lon": -77.1113,
        "radius_m": DEFAULT_RADIUS_M,
        "summary": "A growing Arlington hub with modern buildings, strong Metro access, and an easy balance of convenience and nightlife.",
        "rent_1br": 2450,
        "rent_2br": 3890,
        "rent_3br": 5220,
        "rent_proxy": {"kind": "zip", "region": "22203", "state": "VA"},
    },
    {
        "name": "Dupont Circle",
        "lat": 38.9096,
        "lon": -77.0434,
        "radius_m": DEFAULT_RADIUS_M,
        "summary": "Central, polished, and highly walkable with strong dining options, classic DC housing stock, and convenient access across the city.",
        "rent_1br": 3050,
        "rent_2br": 4825,
        "rent_3br": 6480,
        "rent_proxy": {"kind": "zip", "region": "20036", "state": "DC"},
    },
]

ZILLOW_ZORI_URLS = {
    "zip": "https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv",
    "county": "https://files.zillowstatic.com/research/public_csvs/zori/County_zori_uc_sfrcondomfr_sm_month.csv",
    "city": "https://files.zillowstatic.com/research/public_csvs/zori/City_zori_uc_sfrcondomfr_sm_month.csv",
}


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


def load_existing_records() -> dict[str, dict[str, Any]]:
    if not OUTPUT_PATH.exists():
        return {}

    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {record["name"]: record for record in payload}

    return {record["name"]: record for record in payload.get("neighborhoods", [])}


def latest_date_column(columns: list[str]) -> str:
    date_columns = [column for column in columns if re.fullmatch(r"\d{4}-\d{2}-\d{2}", column)]
    if not date_columns:
        raise ValueError("Could not find Zillow time-series columns in rent CSV")
    return max(date_columns)


def fetch_zillow_rent_proxies() -> tuple[dict[tuple[str, str, str], dict[str, Any]], str | None]:
    proxies: dict[tuple[str, str, str], dict[str, Any]] = {}
    latest_as_of: str | None = None

    for kind, url in ZILLOW_ZORI_URLS.items():
        frame = pd.read_csv(url)
        value_column = latest_date_column(frame.columns.tolist())
        latest_as_of = max(latest_as_of, value_column) if latest_as_of else value_column
        region_column = "RegionName"
        state_column = "StateName"

        for _, row in frame.iterrows():
            region = str(row.get(region_column, "")).strip()
            state = str(row.get(state_column, "")).strip()
            if not region:
                continue

            value = row.get(value_column)
            if pd.isna(value):
                continue

            key = (kind, region.casefold(), state.casefold())
            proxies[key] = {
                "value": float(value),
                "as_of": value_column,
            }

    return proxies, latest_as_of


def compute_rent_values(
    neighborhood: dict[str, Any],
    existing_record: dict[str, Any] | None,
    zillow_proxies: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    proxy_config = neighborhood["rent_proxy"]
    key = (
        proxy_config["kind"],
        str(proxy_config["region"]).casefold(),
        str(proxy_config["state"]).casefold(),
    )
    proxy_info = zillow_proxies.get(key)

    current_proxy = neighborhood["rent_1br"]
    if existing_record:
        current_proxy = (
            existing_record.get("rent_proxy", {}).get("latest_value")
            or existing_record.get("rent_1br")
            or current_proxy
        )

    factor_1br = neighborhood["rent_1br"] / current_proxy if current_proxy else 1.0
    factor_2br = neighborhood["rent_2br"] / current_proxy if current_proxy else 1.0
    factor_3br = neighborhood["rent_3br"] / current_proxy if current_proxy else 1.0

    if existing_record:
        factor_1br = existing_record.get("rent_1br", neighborhood["rent_1br"]) / current_proxy
        factor_2br = existing_record.get("rent_2br", neighborhood["rent_2br"]) / current_proxy
        factor_3br = existing_record.get("rent_3br", neighborhood["rent_3br"]) / current_proxy

    if not proxy_info:
        fallback_as_of = (
            existing_record.get("rent_proxy", {}).get("as_of", "seed estimate")
            if existing_record
            else "seed estimate"
        )
        return {
            "rent_1br": existing_record.get("rent_1br", neighborhood["rent_1br"])
            if existing_record
            else neighborhood["rent_1br"],
            "rent_2br": existing_record.get("rent_2br", neighborhood["rent_2br"])
            if existing_record
            else neighborhood["rent_2br"],
            "rent_3br": existing_record.get("rent_3br", neighborhood["rent_3br"])
            if existing_record
            else neighborhood["rent_3br"],
            "rent_proxy": {
                "source": "Zillow Research ZORI proxy",
                "kind": proxy_config["kind"],
                "region": proxy_config["region"],
                "state": proxy_config["state"],
                "latest_value": current_proxy,
                "as_of": fallback_as_of,
                "status": "fallback",
            },
            "warning": f"{neighborhood['name']}: Zillow proxy {proxy_config['kind']} {proxy_config['region']}, {proxy_config['state']} was unavailable, so previous rent values were kept.",
        }

    latest_value = proxy_info["value"]
    return {
        "rent_1br": round(latest_value * factor_1br),
        "rent_2br": round(latest_value * factor_2br),
        "rent_3br": round(latest_value * factor_3br),
        "rent_proxy": {
            "source": "Zillow Research ZORI proxy",
            "kind": proxy_config["kind"],
            "region": proxy_config["region"],
            "state": proxy_config["state"],
            "latest_value": round(latest_value),
            "as_of": proxy_info["as_of"],
            "status": "updated",
        },
        "warning": None,
    }


def fetch_feature_count(lat: float, lon: float, radius_m: int, tags: dict[str, Any]) -> int:
    features = ox.features_from_point((lat, lon), tags=tags, dist=radius_m)
    if features.empty:
        return 0
    return int(features.index.nunique())


def density_from_count(count: int, radius_m: int) -> float:
    area_sq_km = math.pi * (radius_m**2) / 1_000_000
    return round(count / area_sq_km, 1)


def build_record(
    neighborhood: dict[str, Any],
    existing_record: dict[str, Any] | None,
    zillow_proxies: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    metrics = {}
    for metric_name, tags in METRIC_TAGS.items():
        count = fetch_feature_count(
            neighborhood["lat"],
            neighborhood["lon"],
            neighborhood["radius_m"],
            tags,
        )
        metrics[metric_name] = density_from_count(count, neighborhood["radius_m"])

    rent_values = compute_rent_values(neighborhood, existing_record, zillow_proxies)

    return {
        "name": neighborhood["name"],
        "lat": neighborhood["lat"],
        "lon": neighborhood["lon"],
        "radius_m": neighborhood["radius_m"],
        "summary": neighborhood["summary"],
        "rent_1br": rent_values["rent_1br"],
        "rent_2br": rent_values["rent_2br"],
        "rent_3br": rent_values["rent_3br"],
        "rent_proxy": rent_values["rent_proxy"],
        "metrics": metrics,
    }


def main() -> None:
    ox.settings.use_cache = True
    ox.settings.log_console = True

    existing_records = load_existing_records()
    warnings: list[str] = []
    try:
        zillow_proxies, zillow_latest_as_of = fetch_zillow_rent_proxies()
    except Exception as error:
        print(f"Warning: Zillow rent proxies could not be refreshed ({error})")
        zillow_proxies = {}
        zillow_latest_as_of = None
        warnings.append(
            f"Zillow rent proxy refresh failed entirely, so existing rent values were reused where available. Error: {error}"
        )
    records = [
        build_record(
            neighborhood,
            existing_records.get(neighborhood["name"]),
            zillow_proxies,
        )
        for neighborhood in NEIGHBORHOODS
    ]
    for record in records:
        if record["rent_proxy"]["status"] != "updated":
            warnings.append(
                f"{record['name']}: rent data is using a fallback value from {record['rent_proxy']['as_of']}."
            )
    now = datetime.now(timezone.utc)
    payload = {
        "osm_last_updated": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "osm_last_updated_label": now.strftime("%B %d, %Y"),
        "zillow_last_updated": zillow_latest_as_of,
        "zillow_last_updated_label": zillow_latest_as_of or "Fallback values in use",
        "zillow_method": "Neighborhood rent estimates are scaled from Zillow Research ZORI monthly proxy geographies such as ZIP codes and Arlington County. This keeps rents directionally current without claiming exact block-by-block accuracy.",
        "update_note": "OpenStreetMap metrics refresh from OSM. Rent values are adjusted monthly using Zillow Research ZORI proxy geographies and should be treated as directional estimates.",
        "failures": warnings,
        "neighborhoods": records,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} neighborhoods to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
