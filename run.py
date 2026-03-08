import subprocess, sys, os, time, webbrowser
from threading import Thread


BANNER = """
╔══════════════════════════════════════════════════╗
║   🌍  EarthWatch India  —  Live Intelligence     ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║   Environmental Technology/ Disaster Management  ║
║                                                  ║
║                                                  ║
║   Data Sources:                                  ║
║   ✅  NOAA Cyclone Tracker                      ║
║   ✅  NASA FIRMS Fire                           ║
║   ✅  OpenWeatherMap Flood                      ║
║   ✅  OpenAQ Air Quality                        ║
║   ✅  Indian News NLP                           ║
║                                                  ║
║                                                  ║
╚══════════════════════════════════════════════════╝
"""


def check_packages():
    try:
        import fastapi, uvicorn, requests, feedparser, geopy
        return True
    except ImportError as e:
        print(f"\n❌  Missing package: {e}")
        print("    Run this first:\n")
        print("    pip install -r requirements.txt\n")
        return False


def open_browser():
    time.sleep(3)
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    print(BANNER)

    if not check_packages():
        sys.exit(1)


    from dotenv import load_dotenv
    load_dotenv()
    missing = []
    for key in ["NASA_FIRMS_KEY", "OPENWEATHER_KEY", "OPENAQ_KEY", "MAPBOX_TOKEN"]:
        val = os.getenv(key, "")
        if not val or "your_" in val:
            missing.append(key)

    if missing:
        print("⚠️   Missing API keys in .env:")
        for m in missing:
            print(f"      {m}")
        print("\n    Add them to .env — see API_KEYS_GUIDE.md")
        print("    App will still run, but those data sources will be skipped.\n")

    Thread(target=open_browser, daemon=True).start()

    subprocess.run([
        sys.executable, "-m", "uvicorn", "api.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
    ])
