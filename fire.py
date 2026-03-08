
import requests, csv, io
from datetime import datetime
from geopy.distance import geodesic
from config import NASA_FIRMS_KEY, ZONES

INDIA_BBOX = "68.1766,7.9655,97.4026,35.4940"


def get_fires(days=1):
    if not NASA_FIRMS_KEY or NASA_FIRMS_KEY == "your_firms_key_here":
        print("  ⚠️  Add NASA_FIRMS_KEY to .env  →  firms.modaps.eosdis.nasa.gov/api/")
        return []

    try:
        url  = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{NASA_FIRMS_KEY}/VIIRS_SNPP_NRT/{INDIA_BBOX}/{days}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        fires = []
        for row in csv.DictReader(io.StringIO(resp.text)):
            try:
                if row.get("confidence", "") == "low":
                    continue
                fires.append({
                    "lat":        float(row["latitude"]),
                    "lon":        float(row["longitude"]),
                    "brightness": float(row.get("bright_ti4", 0)),
                    "frp":        float(row.get("frp", 0)),
                    "confidence": row.get("confidence", "nominal"),
                    "datetime":   row.get("acq_date", "") + " " + row.get("acq_time", ""),
                })
            except:
                continue

        print(f"  🔥 NASA FIRMS: {len(fires)} fire detections in India")
        return fires
    except Exception as e:
        print(f"  ⚠️  FIRMS error: {e}")
        return []


def fire_zone_type(lat, lon):

    if 29.5 <= lat <= 32.5 and 73.5 <= lon <= 77.5:
        return "Crop/Stubble Burning"
    
    if 22 <= lat <= 28 and 88 <= lon <= 97:
        return "Forest Fire"
    
    if 29 <= lat <= 32 and 77 <= lon <= 81:
        return "Forest Fire"
    return "Urban/Industrial Fire"


def build_alerts(fires):
    alerts = []
    for fire in fires:
        for zone in ZONES:
            dist = geodesic((fire["lat"], fire["lon"]), (zone["lat"], zone["lon"])).km
            if dist > 50:
                continue

            frp  = fire["frp"]
            ftype = fire_zone_type(fire["lat"], fire["lon"])
            sev  = min(10, 3 + (2 if frp > 100 else 1 if frp > 30 else 0)
                       + (2 if dist < 10 else 1 if dist < 25 else 0)
                       + (2 if ftype == "Forest Fire" else 0))

            alerts.append({
                "type":       "fire",
                "title":      f"🔥 {ftype} — {zone['name']}",
                "location":   zone["name"],
                "state":      zone["state"],
                "lat":        fire["lat"],
                "lon":        fire["lon"],
                "severity":   sev,
                "confidence": fire["confidence"].upper(),
                "source":     "NASA FIRMS (VIIRS)",
                "details": {
                    "Fire Type":        ftype,
                    "Fire Intensity":   f"{frp} MW (Fire Radiative Power)",
                    "Brightness":       f"{fire['brightness']} K",
                    "Distance to City": f"{round(dist)} km from {zone['name']}",
                    "Detection Time":   fire["datetime"],
                    "Satellite":        "VIIRS SNPP (375m resolution)",
                    "NASA Confidence":  fire["confidence"].upper(),
                },
                "damage": {
                    "Air Quality Impact":  "SEVERE" if frp > 100 else "MODERATE",
                    "Health Risk":         "HIGH" if ftype == "Urban/Industrial Fire" else "MODERATE",
                    "Spread Risk":         "HIGH" if ftype == "Forest Fire" else "LOW",
                    "Recommended Action":  action(ftype),
                    "AQI Impact (Est)":    f"+{min(300, int(frp * 1.5))} AQI points",
                },
                "fetched_at": datetime.utcnow().isoformat()
            })
            break  

    
    seen = {}
    for a in alerts:
        key = f"{round(a['lat'], 1)}_{round(a['lon'], 1)}"
        if key not in seen or a["severity"] > seen[key]["severity"]:
            seen[key] = a

    return list(seen.values())


def action(ftype):
    return {
        "Forest Fire":          "Alert Forest Dept. Evacuate nearby villages.",
        "Crop/Stubble Burning": "Notify CPCB & State Pollution Board.",
        "Urban/Industrial Fire": "Alert fire brigade. Check for toxic emissions."
    }.get(ftype, "Alert local authorities.")


def run():
    print("\n🔥 Checking fire detections...")
    fires  = get_fires(days=1)
    alerts = build_alerts(fires)
    print(f"  → {len(alerts)} fire alerts near monitoring zones")
    return alerts


if __name__ == "__main__":
    for a in run():
        print(f"  {a['title']} | Severity {a['severity']} | FRP: {a['details']['Fire Intensity']}")
