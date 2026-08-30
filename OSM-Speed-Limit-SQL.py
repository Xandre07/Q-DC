"""
OpenStreetMap Speed Limit Fetcher, with SQLite implementation
Input: Latitude, Longitude
Output: Speed Limit, Road Name

(C) 2026 Alexandre Teixeira
"""

import requests
import re
import sqlite3
import time
import threading

database = sqlite3.connect("database.db", check_same_thread=False)
cursor = database.cursor()

# 1. Table and R-Tree Index initialization
cursor.executescript("""
    CREATE TABLE IF NOT EXISTS waypoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        speed_limit_kmh INTEGER,
        road_name TEXT
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS waypoints_index USING rtree(
        id,
        min_lat, max_lat,
        min_lon, max_lon
    );
""")

database.commit()
pendingOsmLookups = set()
print("Table created/verified successfully")

def queryLocalDB(lat: float, lon: float) -> int or None:
    query = """
        SELECT w.speed_limit_kmh 
        FROM waypoints w
        JOIN waypoints_index i ON w.id = i.id
        WHERE i.min_lat <= ? AND i.max_lat >= ?
            AND i.min_lon <= ? AND i.max_lon >= ?
        LIMIT 1;
    """
    cursor.execute(query, (lat, lat, lon, lon))
    row = cursor.fetchone()
    return row[0] if row else None

def saveToLocalDB(lat: float, lon: float, limit: int, road_name: str, radius_meters: float = 30.0):
    delta = radius_meters / 111000.0

    cursor.execute("""
        INSERT INTO waypoints (latitude, longitude, speed_limit_kmh, road_name)
        VALUES (?, ?, ?, ?)
    """, (lat, lon, limit, road_name))

    row_id = cursor.lastrowid

    # FIXED: Column names min_lon and max_lon now match the CREATE VIRTUAL TABLE definition
    cursor.execute("""
        INSERT INTO waypoints_index (id, min_lat, max_lat, min_lon, max_lon)
        VALUES (?, ?, ?, ?, ?)
    """, (row_id, lat - delta, lat + delta, lon - delta, lon + delta))

    database.commit()
    print(f"\n[CACHE WRITE] Logged location ({lat}, {lon}) -> Limit: {limit} km/h | Road: '{road_name}'")

def asyncOsmFetch(lat: float, lon: float):
    gridKey = (round(lat, 3), round(lon, 3))

    try:
        osmResult = fetch_speed_limit(lat, lon)
        limit = osmResult.get("speed_limit_kmh") or -1
        road_name = osmResult.get("road_name", "Unknown")

        saveToLocalDB(lat, lon, limit, road_name)
    except Exception as e:
        print(f"\n[ASYNC ERROR] {e}")
    finally:
        pendingOsmLookups.discard(gridKey)

def resolveSpeedLimit(lat: float, lon: float) -> int:
    cached_limit = queryLocalDB(lat, lon)
    if cached_limit is not None:
        return cached_limit

    gridKey = (round(lat, 3), round(lon, 3))
    if gridKey not in pendingOsmLookups:
        pendingOsmLookups.add(gridKey)
        threading.Thread(target=asyncOsmFetch, args=(lat, lon), daemon=True).start()
    return -1

def fetch_speed_limit(latitude: float, longitude: float, radius_meters: int = 50) -> dict:
    delta = radius_meters / 111000.0
    s, w, n, e = latitude - delta, longitude - delta, latitude + delta, longitude + delta

    query = f"""
    [out:json][timeout:5];
    way({s:.6f},{w:.6f},{n:.6f},{e:.6f})["highway"];
    out tags;
    """

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
        return 120
    return None

if __name__ == "__main__":
    test_lat, test_lon = 38.691323, -9.177575

    print("--- Test Run ---")
    
    # First query
    start = time.time()
    res1 = resolveSpeedLimit(lat=test_lat, lon=test_lon)
    elapsed = time.time() - start
    
    if res1 != -1:
        print(f"Result: {res1} km/h [CACHE HIT] ({elapsed:.4f}s)")
    else:
        print(f"Result: -1 [CACHE MISS - Fetching in background...] ({elapsed:.4f}s)")
        
        # Wait only if we had a cache miss to let background thread finish
        time.sleep(3.0) 
        
        # Second query to test the newly populated cache
        start = time.time()
        res2 = resolveSpeedLimit(lat=test_lat, lon=test_lon)
        print(f"Retry Result: {res2} km/h [CACHE HIT] ({time.time() - start:.4f}s)")