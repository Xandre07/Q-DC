# Main package declarations
import time
import sys

# Module declarations
from gps.phyphox import get_latest_phone_gps

def main():
    # Presentation banner for the terminal
    print("==================================================")
    print("Q-DC: Arduino Q Driving Companion (v0.0.1)")
    print("==================================================")

    print("\nRunning demonstration of real-time GPS data streaming with seperate module file")
    print("Connecting to phone GPS stream...")
    print("Press Ctrl+C to exit.\n")

    # Initialize error counter for connection issues
    consecutive_errors = 0

    try:
        while True:
            start_time = time.time()
            
            # Query the external gps_sensor module
            lat, lon, speed_kmh = get_latest_phone_gps()

            if lat is not None and lon is not None:
                consecutive_errors = 0
                latency_ms = (time.time() - start_time) * 1000
                
                # Format output for real-time monitoring
                print(
                    f"[GPS LIVE] "
                    f"Lat: {lat:10.6f} | "
                    f"Lon: {lon:10.6f} | "
                    f"Speed: {speed_kmh:5.1f} km/h | "
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
        print("\n\n[Q-DC] Shutting down main orchestrator safely.")
        sys.exit(0)

if __name__ == "__main__":
    main()