"""
OpenStreetMap Speed Limit Fetcher
Input: Latitude, Longitude
Output: Speed Limit, Road Name

(C) 2026 Alexandre Teixeira
"""

import requests
import re

def fetch_speed_limit(latitude: float, longitude: float, radius_meters: int = 50) -> dict:
    """
    Optimized OSM query: Specifically targets highway ways around coordinates
    with bounding-box pre-filtering to prevent server timeouts.
    """
    # Convert radius in meters to approximate bounding box delta (~111km per degree)
    delta = radius_meters / 111000.0
    s, w, n, e = latitude - delta, longitude - delta, latitude + delta, longitude + delta

    # Bounded query: Scans ONLY highway ways inside the tiny (s,w,n,e) box
    query = f"""
    [out:json][timeout:5];
    way({s:.6f},{w:.6f},{n:.6f},{e:.6f})["highway"];
    out tags;
    """

    # Updated, high-reliability server pool (including French OSM mirror)
    endpoints = [
        "https://overpass.openstreetmap.fr/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]

    headers = {
        'User-Agent': 'ADAS_DrivingCoach_Project/1.0',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }

    response = None
    for url in endpoints:
        try:
            res = requests.post(url, data={'data': query}, headers=headers, timeout=4.0)
            if res.status_code == 200:
                response = res
                break
        except requests.exceptions.RequestException:
            continue

    if response is None:
        return {"status": "ERROR", "speed_limit_kmh": None, "road_name": "Server Error", "raw_tag": None}

    data = response.json()
    elements = data.get("elements", [])

    if not elements:
        return {"status": "NO_ROAD_FOUND", "speed_limit_kmh": None, "road_name": "Off-road / Water", "raw_tag": None}

    road_name = "Unnamed Road"
    maxspeed_tag = None

    # Find the nearest road segment containing maxspeed
    for elem in elements:
        tags = elem.get("tags", {})
        if "name" in tags and road_name == "Unnamed Road":
            road_name = tags.get("name")
        if "maxspeed" in tags:
            maxspeed_tag = tags.get("maxspeed")
            road_name = tags.get("name", road_name)
            break

    if not maxspeed_tag:
        return {"status": "NO_SPEED_LIMIT", "speed_limit_kmh": None, "road_name": road_name, "raw_tag": None}

    speed_kmh = parse_speed_value(maxspeed_tag)

    return {
        "status": "OK",
        "speed_limit_kmh": speed_kmh,
        "road_name": road_name,
        "raw_tag": maxspeed_tag
    }

def parse_speed_value(maxspeed_str: str) -> int or None: # type: ignore
    maxspeed_str = str(maxspeed_str).strip().lower()
    if "mph" in maxspeed_str:
        numbers = re.findall(r'\d+', maxspeed_str)
        if numbers:
            return int(round(int(numbers[0]) * 1.60934))
    numbers = re.findall(r'\d+', maxspeed_str)
    if numbers:
        return int(numbers[0])
    if maxspeed_str == "walk":
        return 10
    elif maxspeed_str == "none":
        return 120  # Fallback max for unrestricted highways
    return None

if __name__ == "__main__":
    # Coordinates to test
    test_lat, test_lon = 38.691323, -9.177575

    print(f"Testing OSM fetch for ({test_lat}, {test_lon})...")
    result = fetch_speed_limit(latitude=test_lat, longitude=test_lon)
    print("\nResult:", result)