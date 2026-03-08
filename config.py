import os
from dotenv import load_dotenv
load_dotenv()

NASA_FIRMS_KEY  = os.getenv("NASA_FIRMS_KEY", "")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY", "")
OPENAQ_KEY      = os.getenv("OPENAQ_KEY", "")
MAPBOX_TOKEN    = os.getenv("MAPBOX_TOKEN", "")
PORT            = int(os.getenv("PORT", 8000))

# India monitoring cities
ZONES = [
    {"name": "Delhi",          "lat": 28.6139, "lon": 77.2090, "state": "Delhi"},
    {"name": "Mumbai",         "lat": 19.0760, "lon": 72.8777, "state": "Maharashtra"},
    {"name": "Kolkata",        "lat": 22.5726, "lon": 88.3639, "state": "West Bengal"},
    {"name": "Chennai",        "lat": 13.0827, "lon": 80.2707, "state": "Tamil Nadu"},
    {"name": "Bengaluru",      "lat": 12.9716, "lon": 77.5946, "state": "Karnataka"},
    {"name": "Hyderabad",      "lat": 17.3850, "lon": 78.4867, "state": "Telangana"},
    {"name": "Bhubaneswar",    "lat": 20.2961, "lon": 85.8245, "state": "Odisha"},
    {"name": "Visakhapatnam",  "lat": 17.6868, "lon": 83.2185, "state": "Andhra Pradesh"},
    {"name": "Guwahati",       "lat": 26.1445, "lon": 91.7362, "state": "Assam"},
    {"name": "Patna",          "lat": 25.5941, "lon": 85.1376, "state": "Bihar"},
    {"name": "Lucknow",        "lat": 26.8467, "lon": 80.9462, "state": "Uttar Pradesh"},
    {"name": "Jaipur",         "lat": 26.9124, "lon": 75.7873, "state": "Rajasthan"},
    {"name": "Ahmedabad",      "lat": 23.0225, "lon": 72.5714, "state": "Gujarat"},
    {"name": "Pune",           "lat": 18.5204, "lon": 73.8567, "state": "Maharashtra"},
    {"name": "Srinagar",       "lat": 34.0837, "lon": 74.7973, "state": "J&K"},
]

# India authority contacts
AUTHORITIES = {
    "cyclone":     "ndma@nic.in",
    "flood":       "ndma@nic.in",
    "fire":        "fsicell-moef@gov.in",
    "air_quality": "cpcb@nic.in",
    "default":     "ndma@nic.in",
}
