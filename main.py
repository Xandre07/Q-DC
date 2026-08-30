# Main package declarations
import time
import sys

# Module declarations
from gps.phyphox import get_latest_phone_gps
from SpeedLimitFetcher import resolveSpeedLimit

def main():
    # Presentation banner for the terminal
    print("==================================================")
    print("Q-DC: Arduino Q Driving Companion (v0.0.2)")
    print("==================================================")

    print("\nRunning demonstration of real-time GPS data streaming and Speed Limit resolution from OpenStreetMap...\n")
    print("Connecting to phone GPS stream...")
    print("Press Ctrl+C to exit.\n")

    # Initialize error counter for connection issues
    consecutive_errors = 0

    try:
        while True:
            start_time = time.time()
            
            # Query the external gps_sensor module
            lat, lon, speed_kmh = get_latest_phone_gps()

            # For testing purposes, we can simulate GPS data here. Only ONE situation should be active at a time. Uncomment the above line to use live GPS data.
            #lat, lon, speed_kmh = 38.731443, -8.999027, 120 # Ponte Vasco da Gama, Lisbon
            #lat, lon, speed_kmh = 38.699958, -9.385106, 50 # Avenida Marginal, Lisbon
            #lat, lon, speed_kmh = 38.786956, -9.242713, 60 # CREL (Casal de Cambra toll), Lisbon
            #lat, lon, speed_kmh = 38.906566, -9.045378, 50 # Populated area near Alverca, Lisbon


            if lat is not None and lon is not None:
                consecutive_errors = 0

                speedLimit = resolveSpeedLimit(lat, lon)

                latency_ms = (time.time() - start_time) * 1000

                # 3. Format output display
                if speedLimit > 0:
                    limit_str = f"{speedLimit:3d} km/h"
                elif speedLimit == -1:
                    limit_str = "FETCHING / UNKNOWN"
                else:
                    limit_str = "NO LIMIT DATA"
                
                # Format output for real-time monitoring
                print(
                    f"[GPS LIVE] "
                    f"Lat: {lat:10.6f} | "
                    f"Lon: {lon:10.6f} | "
                    f"Speed: {speed_kmh:5.1f} km/h | "
                    f"Speed Limit: {limit_str} | "
                    f"Poll Latency: {latency_ms:4.1f}ms"
                )
            else:
                consecutive_errors += 1
                print(f"[GPS SEARCH] Waiting for fix from Phyphox... (Attempt {consecutive_errors})")
                
                # If connection fails repeatedly, back off slightly to prevent CPU spam
                if consecutive_errors > 5:
                    time.sleep(1.0)

            # Polling rate (~2 Hz) for terminal debugging
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n[Q-DC] Stopping...")
        sys.exit(0)

if __name__ == "__main__":
    main()