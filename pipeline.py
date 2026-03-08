"""
pipeline.py  —  Runs all data sources and returns incidents.
Call run() from anywhere to get latest incidents.
"""
from datetime import datetime

# Store incidents in memory (simple — no database needed)
_incidents = []
_last_run  = None


def run():
    global _incidents, _last_run

    print(f"\n{'='*55}")
    print(f"  🌍 EarthWatch India — Running Pipeline")
    print(f"  {datetime.now().strftime('%d %b %Y  %H:%M:%S')}")
    print(f"{'='*55}")

    all_alerts = []

    # 1. Cyclone (no key needed)
    try:
        from data_ingestion.cyclone import run as cyclone_run
        all_alerts.extend(cyclone_run())
    except Exception as e:
        print(f"  Cyclone error: {e}")

    # 2. Flood / Rainfall
    try:
        from data_ingestion.flood import run as flood_run
        all_alerts.extend(flood_run())
    except Exception as e:
        print(f"  Flood error: {e}")

    # 3. Fire (NASA FIRMS)
    try:
        from data_ingestion.fire import run as fire_run
        all_alerts.extend(fire_run())
    except Exception as e:
        print(f"  Fire error: {e}")

    # 4. Air Quality
    try:
        from data_ingestion.air_quality import run as aq_run
        all_alerts.extend(aq_run())
    except Exception as e:
        print(f"  Air quality error: {e}")

    # 5. News NLP
    try:
        from data_ingestion.news import run as news_run
        all_alerts.extend(news_run())
    except Exception as e:
        print(f"  News error: {e}")

    # Aggregate
    from aggregation.engine import run as agg_run
    _incidents = agg_run(all_alerts)
    _last_run  = datetime.utcnow().isoformat()

    print(f"\n✅ Done — {len(_incidents)} incidents | {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*55}\n")

    return _incidents


def get_incidents():
    return _incidents


def get_last_run():
    return _last_run
