import feedparser
from datetime import datetime
from config import ZONES

FEEDS = [
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/2647163.cms",      "src": "Times of India"},
    {"url": "https://www.thehindu.com/sci-tech/energy-and-environment/feeder/default.rss", "src": "The Hindu"},
    {"url": "https://indianexpress.com/section/environment/feed/",            "src": "Indian Express"},
    {"url": "https://www.downtoearth.org.in/rss/all",                         "src": "Down To Earth"},
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/-2128821991.cms",   "src": "TOI India"},
]

KEYWORDS = {
    "cyclone":     ["cyclone","typhoon","storm surge","tauktae","amphan","biparjoy","चक्रवात"],
    "flood":       ["flood","inundation","waterlogging","submerged","dam release","बाढ़"],
    "fire":        ["fire","blaze","wildfire","stubble burn","forest fire","आग"],
    "air_quality": ["pollution","smog","AQI","PM2.5","haze","प्रदूषण"],
    "earthquake":  ["earthquake","tremor","seismic","richter","भूकंप"],
    "landslide":   ["landslide","mudslide","cloudburst","भूस्खलन"],
}

INDIA_CITIES = [
    "Delhi","Mumbai","Kolkata","Chennai","Bengaluru","Hyderabad","Ahmedabad",
    "Pune","Bhubaneswar","Patna","Lucknow","Jaipur","Guwahati","Visakhapatnam",
    "Srinagar","Chandigarh","Bhopal","Nagpur","Coimbatore","Kochi","Odisha",
    "Maharashtra","Assam","Bihar","Uttarakhand","Kerala","Rajasthan","Gujarat",
    "Punjab","Haryana","Andhra Pradesh","Tamil Nadu","West Bengal","Karnataka",
]

CITY_COORDS = {
    "Delhi":(28.6139,77.2090),"Mumbai":(19.0760,72.8777),"Kolkata":(22.5726,88.3639),
    "Chennai":(13.0827,80.2707),"Bengaluru":(12.9716,77.5946),"Hyderabad":(17.3850,78.4867),
    "Ahmedabad":(23.0225,72.5714),"Pune":(18.5204,73.8567),"Bhubaneswar":(20.2961,85.8245),
    "Patna":(25.5941,85.1376),"Lucknow":(26.8467,80.9462),"Jaipur":(26.9124,75.7873),
    "Guwahati":(26.1445,91.7362),"Visakhapatnam":(17.6868,83.2185),"Srinagar":(34.0837,74.7973),
    "Odisha":(20.9517,85.0985),"Maharashtra":(19.7515,75.7139),"Assam":(26.2006,92.9376),
    "Bihar":(25.0961,85.3131),"Uttarakhand":(30.0668,79.0193),"Kerala":(10.8505,76.2711),
    "Rajasthan":(27.0238,74.2179),"Gujarat":(22.2587,71.1924),"Punjab":(31.1471,75.3412),
    "Haryana":(29.0588,76.0856),"West Bengal":(22.9868,87.8550),"Karnataka":(15.3173,75.7139),
}


def scrape():
    articles = []
    for feed in FEEDS:
        try:
            f = feedparser.parse(feed["url"])
            for e in f.entries[:15]:
                articles.append({
                    "title":   e.get("title",""),
                    "summary": e.get("summary","")[:300],
                    "link":    e.get("link",""),
                    "source":  feed["src"],
                    "published": e.get("published",""),
                })
        except:
            pass
    print(f"  📰 Scraped {len(articles)} articles")
    return articles


def classify(article):
    text = (article["title"] + " " + article["summary"]).lower()
    for inc_type, kws in KEYWORDS.items():
        hits = [k for k in kws if k.lower() in text]
        if hits:
            return inc_type, hits
    return None, []


def find_location(article):
    text = article["title"] + " " + article["summary"]
    for city in INDIA_CITIES:
        if city.lower() in text.lower():
            coords = CITY_COORDS.get(city)
            if coords:
                return city, coords[0], coords[1]
    return None, None, None


def build_alerts(articles):
    alerts = []
    seen   = set()

    for art in articles:
        inc_type, kws = classify(art)
        if not inc_type:
            continue

        city, lat, lon = find_location(art)
        if not city:
            continue

        key = f"{inc_type}_{city}_{art['title'][:30]}"
        if key in seen:
            continue
        seen.add(key)

        # Get state from ZONES
        state = next((z["state"] for z in ZONES if z["name"] == city), "India")

        alerts.append({
            "type":       inc_type,
            "title":      f"📰 {art['title'][:80]}",
            "location":   city,
            "state":      state,
            "lat":        lat,
            "lon":        lon,
            "severity":   4,
            "confidence": "MEDIUM",
            "source":     art["source"],
            "details": {
                "Headline":          art["title"],
                "Incident Type":     inc_type.replace("_"," ").title(),
                "Location Detected": city,
                "Keywords Matched":  ", ".join(kws[:5]),
                "News Source":       art["source"],
                "Published":         art["published"],
                "Full Article":      art["link"],
            },
            "damage": {
                "Detection Method":  "NLP Keyword Extraction",
                "Confidence":        "MEDIUM — verify with sensors",
                "Action":            "Cross-reference with satellite & sensor data",
            },
            "fetched_at": datetime.utcnow().isoformat()
        })

    return alerts


def run():
    print("\n📰 Scraping Indian news...")
    articles = scrape()
    alerts   = build_alerts(articles)
    print(f"  → {len(alerts)} news-based signals")
    return alerts


if __name__ == "__main__":
    for a in run()[:5]:
        print(f"  [{a['type']}] {a['title'][:70]}")
