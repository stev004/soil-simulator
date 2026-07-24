"""Explicit one-time downloader for the immutable Phase 9.6 empirical pilot.

This script is intentionally outside the package and is never imported by tests.
Reruns use the checked-in cache and therefore have no network dependency.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from soil_simulator.phase96.empirical import PILOT_LOCATIONS

SOILGRID_PROPERTIES = ("bdod", "cec", "clay", "nitrogen", "phh2o", "sand", "silt", "soc")
SOILGRID_DEPTHS = ("0-5cm", "5-15cm", "15-30cm")
POWER_PARAMETERS = ("T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR")


def _download_json(url: str, destination: Path) -> bool:
    if destination.exists():
        json.loads(destination.read_text(encoding="utf-8"))
        print(f"cached {destination}", flush=True)
        return False
    request = urllib.request.Request(url, headers={"User-Agent": "soil-simulator-phase96/0.9.6"})
    payload: bytes | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read()
            break
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt == 3:
                raise
            print(f"retry {attempt}/3 for {destination}: {exc}", flush=True)
            time.sleep(15.0 * attempt)
    if payload is None:
        raise RuntimeError(f"no payload received for {destination}")
    json.loads(payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    temporary.write_bytes(payload)
    temporary.replace(destination)
    print(f"downloaded {destination}", flush=True)
    return True


def _soilgrids_url(latitude: float, longitude: float) -> str:
    parameters: list[tuple[str, str]] = [("lon", str(longitude)), ("lat", str(latitude))]
    parameters.extend(("property", item) for item in SOILGRID_PROPERTIES)
    parameters.extend(("depth", item) for item in SOILGRID_DEPTHS)
    parameters.append(("value", "Q0.5"))
    return "https://rest.isric.org/soilgrids/v2.0/properties/query?" + urllib.parse.urlencode(
        parameters
    )


def _power_url(parameter: str) -> str:
    query = urllib.parse.urlencode(
        {
            "latitude-min": "49.5",
            "latitude-max": "59.0",
            "longitude-min": "-8.0",
            "longitude-max": "2.0",
            "parameters": parameter,
            "community": "AG",
            "format": "JSON",
            "start": "2001",
            "end": "2020",
        }
    )
    return "https://power.larc.nasa.gov/api/temporal/monthly/regional?" + query


def main() -> None:
    """Download raw source responses, respecting SoilGrids' five-call/minute policy."""
    root = Path(__file__).resolve().parents[1]
    raw = root / "data/raw/phase96_empirical"
    for index, location in enumerate(PILOT_LOCATIONS):
        started = time.monotonic()
        downloaded = _download_json(
            _soilgrids_url(location.latitude_deg, location.longitude_deg),
            raw / "soilgrids" / f"{location.location_id}.json",
        )
        if downloaded and index < len(PILOT_LOCATIONS) - 1:
            time.sleep(max(0.0, 12.1 - (time.monotonic() - started)))
    for parameter in POWER_PARAMETERS:
        _download_json(_power_url(parameter), raw / "nasa_power" / f"{parameter}.json")


if __name__ == "__main__":
    main()
