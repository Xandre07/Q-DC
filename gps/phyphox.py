# gps_sensor.py
import requests
import time

# UPDATE THIS with the IP address shown on your Phyphox screen
PHYPHOX_IP = "192.168.1.209"  
PHYPHOX_PORT = 8080

# Phyphox query format: /get?buffer_name1&buffer_name2
URL = f"http://{PHYPHOX_IP}:{PHYPHOX_PORT}/get?lat&lon&speed"

def get_latest_phone_gps():
    try:
        # Short timeout so main thread never hangs
        response = requests.get(URL, timeout=0.8)
        if response.status_code == 200:
            raw_data = response.json()
            buffer = raw_data.get("buffer", {})

            # Extract buffers safely
            lat_buf = buffer.get("lat", {}).get("buffer", [])
            lon_buf = buffer.get("lon", {}).get("buffer", [])
            speed_buf = buffer.get("speed", {}).get("buffer", [])

            if lat_buf and lon_buf:
                lat = lat_buf[0]
                lon = lon_buf[0]
                speed_mps = speed_buf[0] if speed_buf else 0.0
                speed_kmh = speed_mps * 3.6
                return lat, lon, speed_kmh
    except requests.exceptions.RequestException as e:
        print(f"[CONNECTION WARNING] Cannot reach Phyphox: {e}")
        
    return None, None, None

if __name__ == "__main__":
    print(f"Connecting to Phyphox at {URL}...")
    while True:
        lat, lon, speed = get_latest_phone_gps()
        if lat is not None:
            print(f"[SUCCESS] Lat: {lat:.6f} | Lon: {lon:.6f} | Speed: {speed:.1f} km/h")
        else:
            print("[WAITING] Polling Phyphox... (Ensure experiment is PLAYING ▶ on phone)")
        time.sleep(0.5)