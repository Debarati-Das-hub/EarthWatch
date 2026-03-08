"""
aggregation/engine.py
Combines all signals, deduplicates, scores severity.
"""
from geopy.distance import geodesic
from datetime import datetime
import uuid


def deduplicate(alerts, radius_km=20):
    """Merge alerts of same type within radius_km into one."""
    merged = []
    used   = set()

    for i, a in enumerate(alerts):
        if i in used:
            continue

        group = [a]
        used.add(i)

        for j, b in enumerate(alerts):
            if j in used or a["type"] != b["type"]:
                continue
            if not (a.get("lat") and b.get("lat")):
                continue
            dist = geodesic((a["lat"], a["lon"]), (b["lat"], b["lon"])).km
            if dist <= radius_km:
                group.append(b)
                used.add(j)

        # Take highest severity from the group
        best = max(group, key=lambda x: x.get("severity", 0))

        # Count unique sources across group
        sources = list({g["source"] for g in group})
        conf    = "HIGH" if len(sources) >= 3 else ("MEDIUM" if len(sources) == 2 else best["confidence"])

        merged.append({
            **best,
            "id":           str(uuid.uuid4()),
            "source_list":  sources,
            "source_count": len(sources),
            "confidence":   conf,
            "severity":     min(10, best.get("severity", 1) + (1 if len(sources) > 1 else 0)),
            "detected_at":  datetime.utcnow().isoformat(),
        })

    return sorted(merged, key=lambda x: x.get("severity", 0), reverse=True)


def run(all_alerts):
    print(f"\n⚙️  Aggregating {len(all_alerts)} raw signals...")
    incidents = deduplicate(all_alerts)
    print(f"  → {len(incidents)} unique incidents")

    high = sum(1 for i in incidents if i.get("severity", 0) >= 7)
    med  = sum(1 for i in incidents if 4 <= i.get("severity", 0) < 7)
    low  = sum(1 for i in incidents if i.get("severity", 0) < 4)
    print(f"  High: {high} | Medium: {med} | Low: {low}")

    return incidents
