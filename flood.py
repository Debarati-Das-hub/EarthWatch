
import requests
from datetime import datetime
from config import OPENWEATHER_KEY, ZONES


def get_weather(zone):
    if not OPENWEATHER_KEY or OPENWEATHER_KEY == "your_openweather_key_here":
        print("  ⚠️  Add OPENWEATHER_KEY to .env  →  openweathermap.org/api")
        return None
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": zone["lat"], "lon": zone["lon"],
                    "appid": OPENWEATHER_KEY, "units": "metric"},
            timeout=10
        )
        r.raise_for_status()
        d = r.json()

        rain_1h = d.get("rain", {}).get("1h", 0)
        rain_3h = d.get("rain", {}).get("3h", 0)
        temp    = d.get("main", {}).get("temp", 0)
        humid   = d.get("main", {}).get("humidity", 0)
        desc    = d.get("weather", [{}])[0].get("description", "").title()
        wind_ms = d.get("wind", {}).get("speed", 0)
        wind_kh = round(wind_ms * 3.6)

        
        if rain_1h > 50 or rain_3h > 100:
            risk, sev = "EXTREME", 9
        elif rain_1h > 20 or rain_3h > 50:
            risk, sev = "VERY HIGH", 7
        elif rain_1h > 7.5 or rain_3h > 20:
            risk, sev = "HIGH", 5
        elif rain_1h > 2.5 or rain_3h > 7.5:
            risk, sev = "MODERATE", 3
        else:
            risk, sev = "LOW", 0

        return {
            "zone":     zone,
            "rain_1h":  rain_1h,
            "rain_3h":  rain_3h,
            "temp":     temp,
            "humidity": humid,
            "desc":     desc,
            "wind_kmh": wind_kh,
            "risk":     risk,
            "severity": sev,
        }
    except Exception as e:
        print(f"    ⚠️  Weather error {zone['name']}: {e}")
        return None


def build_alerts(weather_data):
    alerts = []
    for w in weather_data:
        if not w or w["severity"] < 3:
            continue

        zone = w["zone"]
        r1   = w["rain_1h"]
        r3   = w["rain_3h"]

        alerts.append({
            "type":       "flood",
            "title":      f"🌊 Flood Risk — {zone['name']} ({w['risk']})",
            "location":   zone["name"],
            "state":      zone["state"],
            "lat":        zone["lat"],
            "lon":        zone["lon"],
            "severity":   w["severity"],
            "confidence": "HIGH" if w["severity"] >= 7 else "MEDIUM",
            "source":     "OpenWeatherMap",
            "details": {
                "Flood Risk Level":   w["risk"],
                "Rainfall (1 hour)":  f"{r1} mm",
                "Rainfall (3 hours)": f"{r3} mm",
                "Temperature":        f"{w['temp']} °C",
                "Humidity":           f"{w['humidity']}%",
                "Wind Speed":         f"{w['wind_kmh']} km/h",
                "Sky Condition":      w["desc"],
                "IMD Category":       imd_rain_cat(r1),
            },
            "damage": {
                "Homes at Risk":       flood_homes(w["severity"]),
                "Roads Affected":      flood_roads(w["severity"]),
                "Crop Damage":         flood_crops(w["severity"]),
                "Evacuation Needed":   "YES" if w["severity"] >= 7 else "Monitor",
                "Economic Loss (Est)": flood_loss(w["severity"]),
                "Alert to":            "NDMA + State Disaster Authority",
            },
            "fetched_at": datetime.utcnow().isoformat()
        })

    return alerts


def imd_rain_cat(r1):
    if r1 > 50:   return "Extremely Heavy Rain (IMD Red Alert)"
    if r1 > 20:   return "Very Heavy Rain (IMD Orange Alert)"
    if r1 > 7.5:  return "Heavy Rain (IMD Yellow Alert)"
    if r1 > 2.5:  return "Moderate Rain"
    return "Light Rain"

def flood_homes(s):
    if s >= 9: return "CRITICAL — 10,000+ homes"
    if s >= 7: return "HIGH — 1,000–10,000 homes"
    if s >= 5: return "MODERATE — 100–1,000 homes"
    return "LOW — Under 100 homes"

def flood_roads(s):
    if s >= 9: return "Multiple highways blocked"
    if s >= 7: return "Major roads flooded"
    if s >= 5: return "Low-lying roads at risk"
    return "Minor disruption"

def flood_crops(s):
    if s >= 9: return "EXTENSIVE — widespread loss"
    if s >= 7: return "SEVERE — significant loss"
    if s >= 5: return "MODERATE"
    return "MINIMAL"

def flood_loss(s):
    if s >= 9: return "₹100 Crore+"
    if s >= 7: return "₹10–100 Crore"
    if s >= 5: return "₹1–10 Crore"
    return "Under ₹1 Crore"


def run():
    print("\n🌊 Checking rainfall & flood risk...")
    data   = [get_weather(z) for z in ZONES]
    alerts = build_alerts(data)
    print(f"  → {len(alerts)} flood alerts")
    return alerts


if __name__ == "__main__":
    for a in run():
        print(f"  {a['title']} | Severity {a['severity']}")
