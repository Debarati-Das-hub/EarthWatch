"""
data_ingestion/air_quality.py
Real AQI from OpenAQ v3 API — FULLY CORRECT 2025 implementation
Verified response structure from working v3 examples.

Flow per city:
  1. GET /v3/locations?coordinates=lat,lon&radius=25000&limit=10
       → find location IDs + sensor IDs for pm25/pm10/no2
  2. GET /v3/locations/{loc_id}/latest
       → results[i] = {sensorsId, value, locationsId, datetime, coordinates}
       → match sensorsId to get pm25 value
"""
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from config import OPENAQ_KEY, ZONES

BASE    = "https://api.openaq.org/v3"
RADIUS  = 25000   # 25 km — max allowed by OpenAQ v3
TIMEOUT = 20


def _headers():
    h = {"Accept": "application/json"}
    if OPENAQ_KEY and OPENAQ_KEY not in ("", "your_openaq_key_here"):
        h["X-API-Key"] = OPENAQ_KEY
    return h


# ── Step 1: find nearby locations and their sensor IDs ─────────────────────

def find_pm25_sensors(lat, lon):
    """
    Returns list of {loc_id, loc_name, sensor_id, param_name} dicts
    for pm25 (and pm10/no2) sensors within RADIUS of the given point.
    coordinates param must be "lat,lon" per v3 docs.
    """
    try:
        r = requests.get(
            f"{BASE}/locations",
            params={
                "coordinates": f"{lat},{lon}",
                "radius":      RADIUS,
                "limit":       10,
            },
            headers=_headers(),
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return []

        sensors_found = []
        for loc in r.json().get("results", []):
            loc_id   = loc.get("id")
            loc_name = loc.get("name", "Station")
            for s in loc.get("sensors", []):
                pname = s.get("parameter", {}).get("name", "").lower()
                if pname in ("pm25", "pm2.5", "pm10", "no2"):
                    sensors_found.append({
                        "loc_id":    loc_id,
                        "loc_name":  loc_name,
                        "sensor_id": s.get("id"),
                        "param":     "pm25" if pname in ("pm25","pm2.5") else pname,
                    })
        return sensors_found

    except Exception as e:
        return []


# ── Step 2: get latest readings for a location ─────────────────────────────

def fetch_latest(loc_id):
    """
    GET /v3/locations/{loc_id}/latest
    Returns list of {sensorsId, value, datetime} dicts.
    """
    try:
        r = requests.get(
            f"{BASE}/locations/{loc_id}/latest",
            headers=_headers(),
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return []
        return r.json().get("results", [])
    except Exception:
        return []


# ── Main per-zone function ─────────────────────────────────────────────────

def get_aqi(zone):
    try:
        lat, lon = zone["lat"], zone["lon"]

        # Find sensors near this city
        sensors = find_pm25_sensors(lat, lon)
        if not sensors:
            return None

        # Group by location so we only call /latest once per location
        locs = {}
        for s in sensors:
            lid = s["loc_id"]
            if lid not in locs:
                locs[lid] = {"name": s["loc_name"], "sensors": {}}
            locs[lid]["sensors"][s["sensor_id"]] = s["param"]

        # Fetch latest for each location, collect readings
        readings = {"pm25": None, "pm10": None, "no2": None}
        station  = zone["name"]

        for lid, info in locs.items():
            latest = fetch_latest(lid)
            if not latest:
                continue
            station = info["name"]
            for reading in latest:
                sid   = reading.get("sensorsId")
                val   = reading.get("value")
                param = info["sensors"].get(sid)
                if param and val is not None and float(val) > 0:
                    if readings[param] is None:      # take first valid reading
                        readings[param] = round(float(val), 1)
            # Stop if we have pm25
            if readings["pm25"] is not None:
                break

        if readings["pm25"] is None:
            return None

        pm25 = readings["pm25"]
        aqi  = pm25_to_aqi(pm25)
        cat  = aqi_category(aqi)

        return {
            "zone":    zone,
            "pm25":    pm25,
            "pm10":    readings["pm10"],
            "no2":     readings["no2"],
            "aqi":     aqi,
            "category": cat,
            "station": station,
        }

    except Exception as e:
        print(f"    ⚠️  AQ error {zone['name']}: {e}")
        return None


# ── AQI conversion (India CPCB scale) ─────────────────────────────────────

def pm25_to_aqi(pm25):
    bp = [
        (0,   30,  0,   50),
        (30,  60,  51,  100),
        (60,  90,  101, 200),
        (90,  120, 201, 300),
        (120, 250, 301, 400),
        (250, 500, 401, 500),
    ]
    for cl, ch, il, ih in bp:
        if cl <= pm25 <= ch:
            return round(((ih - il) / (ch - cl)) * (pm25 - cl) + il)
    return 500


def aqi_category(aqi):
    if aqi <= 50:  return {"label": "Good",         "color": "#22c55e", "sev": 1}
    if aqi <= 100: return {"label": "Satisfactory", "color": "#84cc16", "sev": 3}
    if aqi <= 200: return {"label": "Moderate",     "color": "#eab308", "sev": 5}
    if aqi <= 300: return {"label": "Poor",         "color": "#f97316", "sev": 7}
    if aqi <= 400: return {"label": "Very Poor",    "color": "#ef4444", "sev": 8}
    return               {"label": "Severe",        "color": "#7c3aed", "sev": 10}


# ── Build alert objects ────────────────────────────────────────────────────

def build_alerts(aq_data):
    alerts = []
    for d in aq_data:
        if not d:
            continue
        zone = d["zone"]
        aqi  = d["aqi"]
        cat  = d["category"]
        pm25 = d["pm25"]

        # Show anything Moderate (sev>=5) or worse
        if cat["sev"] < 5:
            continue

        alerts.append({
            "type":       "air_quality",
            "title":      f"😷 {cat['label']} Air — {zone['name']} (AQI {aqi})",
            "location":   zone["name"],
            "state":      zone["state"],
            "lat":        zone["lat"],
            "lon":        zone["lon"],
            "severity":   cat["sev"],
            "confidence": "HIGH",
            "source":     "OpenAQ / CPCB India",
            "aqi_color":  cat["color"],
            "details": {
                "AQI (India CPCB)":     f"{aqi} — {cat['label']}",
                "PM2.5":                f"{pm25} µg/m³  (WHO safe: 15 µg/m³)",
                "PM10":                 f"{d['pm10']} µg/m³" if d["pm10"] else "N/A",
                "NO2":                  f"{d['no2']} µg/m³"  if d["no2"]  else "N/A",
                "Station":              d["station"],
                "Times Over WHO Limit": f"{round(pm25/15,1)}x",
                "Primary Source":       pollution_source(zone["name"]),
            },
            "damage": {
                "Health Risk":        health_risk(aqi),
                "Sensitive Groups":   sensitive_groups(aqi),
                "Recommended Action": action(aqi),
                "School Closure":     "RECOMMENDED" if aqi > 400 else "Not required",
                "Outdoor Activity":   "BANNED" if aqi > 400 else ("AVOID" if aqi > 300 else "LIMIT"),
            },
            "fetched_at": datetime.utcnow().isoformat(),
        })
    return alerts


# ── Helper text functions ──────────────────────────────────────────────────

def pollution_source(city):
    return {
        "Delhi":         "Vehicles + stubble burning + industry",
        "Mumbai":        "Vehicles + construction + sea salt",
        "Kolkata":       "Vehicles + industry + coal",
        "Lucknow":       "Vehicles + construction dust",
        "Patna":         "Vehicles + crop burning",
        "Hyderabad":     "Vehicles + construction",
        "Chennai":       "Vehicles + industry + sea",
        "Bengaluru":     "Vehicles + construction dust",
        "Ahmedabad":     "Vehicles + textile industry",
        "Jaipur":        "Vehicles + dust storms",
        "Visakhapatnam": "Industry + port + vehicles",
        "Guwahati":      "Vehicles + biomass burning",
        "Bhubaneswar":   "Vehicles + industry",
        "Pune":          "Vehicles + construction",
        "Srinagar":      "Vehicles + wood burning (winter)",
    }.get(city, "Vehicles + industrial emissions")


def health_risk(aqi):
    if aqi > 400: return "SEVERE — all outdoor activity dangerous"
    if aqi > 300: return "VERY HIGH — avoid outdoor exposure"
    if aqi > 200: return "HIGH — sensitive groups severely affected"
    return "MODERATE — reduce prolonged outdoor activity"


def sensitive_groups(aqi):
    if aqi > 300: return "ALL people affected — especially children & elderly"
    return "Children, elderly, asthma & heart patients"


def action(aqi):
    if aqi > 400: return "Stay indoors. Run air purifier. Wear N95 mask."
    if aqi > 300: return "Limit outdoor time. Wear N95 mask."
    return "Wear mask outdoors. Avoid exercise outside."


# ── Main entry point ───────────────────────────────────────────────────────

def run():
    print("\n😷 Checking air quality across India (parallel)...")
    if not OPENAQ_KEY or OPENAQ_KEY in ("", "your_openaq_key_here"):
        print("  ⚠️  Add OPENAQ_KEY to .env")
        return []

    # Fetch all zones in parallel — much faster
    data = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(get_aqi, z): z for z in ZONES}
        for fut in as_completed(futures):
            result = fut.result()
            data.append(result)
            z = futures[fut]
            if result:
                print(f"  ✅ {z['name']}: PM2.5={result['pm25']} AQI={result['aqi']} ({result['category']['label']})")
            else:
                print(f"  ⚪ {z['name']}: no data")

    alerts = build_alerts(data)
    found  = sum(1 for d in data if d is not None)
    print(f"\n  → {found}/{len(ZONES)} stations with data | {len(alerts)} alerts generated")
    return alerts


if __name__ == "__main__":
    for a in run():
        print(f"\n  {a['title']}")
        print(f"  PM2.5: {a['details']['PM2.5']}")
        print(f"  Station: {a['details']['Station']}")