"""
data_ingestion/cyclone.py
Tracks Bay of Bengal & Arabian Sea cyclones.
NO API KEY NEEDED — uses free NOAA data.
"""
import requests
from geopy.distance import geodesic
from datetime import datetime
from config import ZONES


def get_active_cyclones():
    """Fetch active cyclones from NOAA. No key needed."""
    try:
        url  = "https://www.nhc.noaa.gov/CurrentStorms.json"
        resp = requests.get(url, timeout=10)
        data = resp.json()

        results = []
        for s in data.get("activeStorms", []):
            try:
                wind_mph = float(s.get("intensity", 0))
                wind_kmh = round(wind_mph * 1.60934)
                lat      = float(s.get("latitudeNumeric", 0))
                lon      = float(s.get("longitudeNumeric", 0))

                results.append({
                    "id":     s.get("id", ""),
                    "name":   s.get("name", "Unnamed"),
                    "wind_kmh": wind_kmh,
                    "lat":    lat,
                    "lon":    lon,
                    "classification": classify(wind_kmh),
                    "source": "NOAA NHC"
                })
            except:
                continue

        print(f"  🌀 Cyclones found: {len(results)}")
        return results
    except Exception as e:
        print(f"  ⚠️  Cyclone fetch error: {e}")
        return []


def classify(wind_kmh):
    if wind_kmh < 62:   return "Low Pressure"
    if wind_kmh < 89:   return "Depression"
    if wind_kmh < 118:  return "Cyclonic Storm"
    if wind_kmh < 168:  return "Severe Cyclonic Storm"
    if wind_kmh < 222:  return "Very Severe Cyclonic Storm"
    return "Super Cyclonic Storm"


def build_alerts(cyclones):
    alerts = []
    for cyc in cyclones:
        for zone in ZONES:
            dist = geodesic((cyc["lat"], cyc["lon"]), (zone["lat"], zone["lon"])).km
            if dist > 800:
                continue

            sev = 10 if dist < 100 else (8 if dist < 300 else (5 if dist < 600 else 3))

            alerts.append({
                "type":          "cyclone",
                "title":         f"🌀 Cyclone {cyc['name']} — {zone['name']}",
                "location":      zone["name"],
                "state":         zone["state"],
                "lat":           zone["lat"],
                "lon":           zone["lon"],
                "severity":      sev,
                "confidence":    "HIGH" if dist < 300 else "MEDIUM",
                "source":        "NOAA NHC",
                "details": {
                    "Cyclone Name":      cyc["name"],
                    "Classification":    cyc["classification"],
                    "Wind Speed":        f"{cyc['wind_kmh']} km/h",
                    "Distance":          f"{round(dist)} km from {zone['name']}",
                    "Storm Surge Risk":  surge(cyc["wind_kmh"]),
                    "Evacuation Needed": "YES" if dist < 200 else "Monitor situation",
                    "Affected State":    zone["state"],
                },
                "damage": {
                    "Structures at Risk":  risk_structures(cyc["wind_kmh"]),
                    "Crop Damage":         risk_crops(cyc["wind_kmh"]),
                    "Power Outage Risk":   "HIGH" if cyc["wind_kmh"] > 100 else "MEDIUM",
                    "Economic Loss (Est)": econ_loss(cyc["wind_kmh"]),
                    "People at Risk":      people_risk(dist),
                },
                "fetched_at": datetime.utcnow().isoformat()
            })

    return alerts


def surge(w):
    if w > 200: return "Extreme (5–7m)"
    if w > 150: return "Very High (3–5m)"
    if w > 100: return "High (1.5–3m)"
    return "Moderate (0.5–1.5m)"

def risk_structures(w):
    if w > 150: return "SEVERE — >10,000 structures"
    if w > 100: return "HIGH — 1,000–10,000 structures"
    return "MODERATE"

def risk_crops(w):
    if w > 150: return "EXTENSIVE"
    if w > 100: return "SEVERE"
    return "MODERATE"

def econ_loss(w):
    if w > 150: return "₹500 Crore+"
    if w > 100: return "₹50–500 Crore"
    return "₹10–50 Crore"

def people_risk(d):
    if d < 100: return "500,000+"
    if d < 300: return "100,000–500,000"
    return "Under assessment"


def run():
    print("\n🌀 Checking cyclones...")
    cyclones = get_active_cyclones()
    return build_alerts(cyclones)


if __name__ == "__main__":
    for a in run():
        print(f"  {a['title']} | Severity {a['severity']}")
