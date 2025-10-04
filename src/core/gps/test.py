#!/usr/bin/env python3
"""
Robust L76X GNSS logger + board-state printer.

- Safe with/without SRTM (no AttributeError).
- Prints a compact state line every second:
  FIX, PPS-expected, SatsUsed, SatsView, HDOP, Lat/Lon, Speed, Course, Elev-AGL.
- Logs to coordinates.csv (UTC timestamp + fields).
- Watchdog: if no NMEA for > NO_NMEA_TIMEOUT_SEC, tries Exit_BackupMode() + warm start; after repeats, cold start.
"""

import time
import csv
import os
from datetime import datetime

import L76X  # Provided by Waveshare L76K library

# ===================== User toggles =====================
USE_SRTM = False            # True to enable terrain elevation lookups (slower)
CSV_PATH = "coordinates.csv"
BAUD = 9600
POS_FIX_INTERVAL_MS = 400   # 400 (~2.5 Hz) or 1000 (1 Hz)

# Watchdog knobs
NO_NMEA_TIMEOUT_SEC = 5             # If no NMEA updates for this many seconds, attempt recovery
MAX_CONSEC_TIMEOUTS_BEFORE_COLD = 3 # After this many consecutive timeouts, do a cold start
# ========================================================


# ---- SRTM shim so L76X.get_gps_data(elev) always has a .get_elevation() ----
class _NoElevation:
    def get_elevation(self, lat, lon):
        # Return None to indicate "unknown"; change to 0.0 if you prefer sea level baseline
        return None

if USE_SRTM:
    try:
        import srtm
        ELEV = srtm.get_data()
    except Exception as e:
        print(f"[WARN] Failed to init SRTM data ({e}); continuing without elevation.")
        ELEV = _NoElevation()
else:
    ELEV = _NoElevation()


def ensure_csv(path):
    new_file = not os.path.exists(path)
    f = open(path, "a", newline="")
    writer = csv.writer(f)
    if new_file:
        writer.writerow([
            "iso_time_utc", "fix_status", "pps_expected",
            "lat", "lon", "speed_mps", "course_deg",
            "elev_above_ground_m", "sat_used", "sat_in_view", "hdop"
        ])
    return f, writer


def pps_expected_from_status(fix_status: int) -> bool:
    """
    Many L76X examples set Status == 1 when 'positioned'.
    Treat that as "PPS expected". Adjust if your lib exposes a finer-grained fix_type.
    """
    return int(fix_status or 0) == 1


def configure_gnss(gps: L76X.L76X):
    """Set baud, rate, NMEA selection, and exit any backup/standby state."""
    gps.L76X_Set_Baudrate(BAUD)

    # Set position fix interval / output rate
    try:
        if POS_FIX_INTERVAL_MS == 400 and hasattr(gps, "SET_POS_FIX_400MS"):
            gps.L76X_Send_Command(gps.SET_POS_FIX_400MS)
        elif POS_FIX_INTERVAL_MS == 1000 and hasattr(gps, "SET_POS_FIX_1000MS"):
            gps.L76X_Send_Command(gps.SET_POS_FIX_1000MS)
        elif hasattr(gps, "SET_POS_FIX_400MS"):
            gps.L76X_Send_Command(gps.SET_POS_FIX_400MS)
    except Exception:
        pass

    # Enable default NMEA output set (library preset)
    try:
        if hasattr(gps, "SET_NMEA_OUTPUT"):
            gps.L76X_Send_Command(gps.SET_NMEA_OUTPUT)
    except Exception:
        pass

    # Make sure we’re awake
    try:
        gps.L76X_Exit_BackupMode()
    except Exception:
        pass


def _getattr_any(obj, *names, default=None):
    """Return the first existing attribute value among names, else default."""
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return default


def print_state(gps):
    """Emit a compact, greppable single-line state summary."""
    # Time from module
    hh = _getattr_any(gps, "Time_H", default=None)
    mm = _getattr_any(gps, "Time_M", default=None)
    ss = _getattr_any(gps, "Time_S", default=None)
    try:
        tstr = f"{int(hh):02}:{int(mm):02}:{int(ss):02}" if hh is not None else "--:--:--"
    except Exception:
        tstr = "--:--:--"

    # Core fields with safe defaults
    fix = int(_getattr_any(gps, "Status", default=0) or 0)

    # Satellites used (from GGA/GSA)
    sats_used = _getattr_any(
        gps,
        "satellites_used", "Satellites", "sats_used",
        default=None
    )

    # Satellites in view (from GSV) – try common attribute names
    sats_in_view = _getattr_any(
        gps,
        "satellites_in_view", "SatellitesInView", "gsv_in_view", "sats_in_view",
        default=None
    )

    hdop = _getattr_any(gps, "hdop", "HDOP", default=None)

    try:
        lat = float(_getattr_any(gps, "Lat", default=0.0) or 0.0)
        lon = float(_getattr_any(gps, "Lon", default=0.0) or 0.0)
    except Exception:
        lat, lon = 0.0, 0.0

    spd = float(_getattr_any(gps, "speed", "Speed", default=0.0) or 0.0)
    crs = float(_getattr_any(gps, "course", "Course", default=0.0) or 0.0)
    eag = float(_getattr_any(gps, "elevation_above_ground", "elevation", default=0.0) or 0.0)

    pps = pps_expected_from_status(fix)

    print(
        f"[{tstr}] FIX={fix} PPS={'Y' if pps else 'N'} "
        f"SatsUsed={sats_used if sats_used is not None else '-'} "
        f"SatsView={sats_in_view if sats_in_view is not None else '-'} "
        f"HDOP={hdop if hdop is not None else '-'} "
        f"Lat={lat:.6f} Lon={lon:.6f} "
        f"Spd={spd:.2f} m/s Crs={crs:.1f}° EAG={eag:.1f} m"
    )

    # Return values used by the logger
    return fix, pps, lat, lon, spd, crs, eag, sats_used, sats_in_view, hdop


def main():
    gps = L76X.L76X()
    configure_gnss(gps)

    f, writer = ensure_csv(CSV_PATH)

    last_nmea_ts = time.time()
    consecutive_timeouts = 0

    try:
        while True:
            # Pull a new sample; tolerate elevation provider issues
            try:
                gps.get_gps_data(ELEV)
            except Exception as e:
                # If the library still tries to call get_elevation(None,...), re-call with a stub
                print(f"[WARN] gps.get_gps_data failed: {e}; retrying with no-elevation stub.")
                gps.get_gps_data(_NoElevation())

            now = time.time()

            # Consider we have "any NMEA" if time fields updated
            got_any_nmea = _getattr_any(gps, "Time_H", default=None) is not None
            if got_any_nmea:
                last_nmea_ts = now
                consecutive_timeouts = 0

            # Print one-line state and capture values for CSV
            fix, pps, lat, lon, spd, crs, eag, sats_used, sats_in_view, hdop = print_state(gps)

            # Log to CSV every loop; consumers can filter by fix later
            writer.writerow([
                datetime.utcnow().isoformat(timespec="seconds") + "Z",
                fix,
                int(pps),
                f"{lat:.7f}",
                f"{lon:.7f}",
                f"{spd:.3f}",
                f"{crs:.3f}",
                f"{eag:.3f}",
                sats_used if sats_used is not None else "",
                sats_in_view if sats_in_view is not None else "",
                hdop if hdop is not None else ""
            ])
            f.flush()

            # Watchdog: if NMEA has been silent for too long, attempt recovery
            silence = now - last_nmea_ts
            if silence > NO_NMEA_TIMEOUT_SEC:
                consecutive_timeouts += 1
                print(f"[WARN] No NMEA for {int(silence)}s; attempting wake…")
                try:
                    gps.L76X_Exit_BackupMode()
                except Exception:
                    pass

                # Prefer warm start first; then cold if repeatedly failing
                did_action = False
                try:
                    if hasattr(gps, "SET_WARM_START"):
                        gps.L76X_Send_Command(gps.SET_WARM_START)
                        print("[ACTION] Warm start command sent.")
                        did_action = True
                except Exception:
                    pass

                if not did_action and hasattr(gps, "L76X_Warm_Start"):
                    try:
                        gps.L76X_Warm_Start()
                        print("[ACTION] Warm start (alt API) invoked.")
                        did_action = True
                    except Exception:
                        pass

                if consecutive_timeouts >= MAX_CONSEC_TIMEOUTS_BEFORE_COLD:
                    try:
                        if hasattr(gps, "SET_FULL_COLD_START"):
                            gps.L76X_Send_Command(gps.SET_FULL_COLD_START)
                            print("[ACTION] Cold start command sent.")
                            consecutive_timeouts = 0
                        elif hasattr(gps, "L76X_Cold_Start"):
                            gps.L76X_Cold_Start()
                            print("[ACTION] Cold start (alt API) invoked.")
                            consecutive_timeouts = 0
                    except Exception:
                        pass

                # Give the receiver a moment to spin up
                time.sleep(1.0)
                continue

            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nProgram end")
    finally:
        try:
            f.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
