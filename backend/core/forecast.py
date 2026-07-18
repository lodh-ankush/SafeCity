# core/forecast.py
"""
Time-series forecasting module.
Analyses historical incident data to predict hotspot times, days, and risk zones.
"""
from datetime import datetime
from collections import defaultdict, Counter
from core.db import read_incidents, read_events


def generate_forecast():
    """
    Return forecasting payload based on historical patterns:
    - hotspot_hours: per-hour risk predictions
    - trend: overall direction (increasing / stable / decreasing)
    - daily_averages: average incidents per day-of-week
    - risk_zones: geo-clustered areas ranked by incident count
    - hourly_timeline: hour-by-hour incident counts for charting
    """
    incidents = read_incidents()
    events = read_events()

    empty = {
        "hotspot_hours": [],
        "trend": "insufficient_data",
        "daily_averages": {},
        "risk_zones": [],
        "hourly_timeline": [],
        "type_distribution": {},
    }

    if len(incidents) < 3:
        return empty

    # ── Hourly pattern ──────────────────────────────────────────────
    hourly_counts = Counter()
    daily_counts = defaultdict(int)
    type_counts = Counter()
    parsed_dates = []

    for inc in incidents:
        try:
            dt = datetime.strptime(inc["timestamp"], "%Y-%m-%d %H:%M:%S")
            hourly_counts[dt.hour] += 1
            daily_counts[dt.strftime("%A")] += 1
            type_counts[inc.get("type", "unknown")] += 1
            parsed_dates.append(dt)
        except (ValueError, KeyError):
            continue

    total = sum(hourly_counts.values()) or 1

    hotspot_hours = []
    for hour in range(24):
        count = hourly_counts.get(hour, 0)
        rate = count / total
        risk = (
            "critical" if rate > 0.12 else
            "high"     if rate > 0.08 else
            "medium"   if rate > 0.04 else
            "low"
        )
        hotspot_hours.append({
            "hour": hour,
            "predicted_count": round(count * 1.05, 1),
            "actual_count": count,
            "risk_level": risk,
        })

    # ── Daily averages ──────────────────────────────────────────────
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    num_weeks = max(1, (max(parsed_dates) - min(parsed_dates)).days / 7) if parsed_dates else 1
    daily_avgs = {
        d: round(daily_counts.get(d, 0) / num_weeks, 2)
        for d in days_order
    }

    # ── Trend analysis ──────────────────────────────────────────────
    if parsed_dates:
        sorted_dates = sorted(parsed_dates)
        mid = len(sorted_dates) // 2
        first_half = mid or 1
        second_half = (len(sorted_dates) - mid) or 1
        if mid > 0:
            first_span = max((sorted_dates[mid - 1] - sorted_dates[0]).days, 1)
            second_span = max((sorted_dates[-1] - sorted_dates[mid]).days, 1)
            first_rate = first_half / first_span
            second_rate = second_half / second_span
            trend = (
                "increasing" if second_rate > first_rate * 1.15 else
                "decreasing" if second_rate < first_rate * 0.85 else
                "stable"
            )
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"

    # ── Risk zones from geo clusters ────────────────────────────────
    risk_zones = []
    geo_clusters = defaultdict(list)

    for inc in incidents:
        lat, lon = inc.get("lat"), inc.get("lon")
        if lat is not None and lon is not None:
            key = (round(lat, 2), round(lon, 2))
            geo_clusters[key].append(inc)

    for (lat, lon), cluster in sorted(
        geo_clusters.items(), key=lambda x: len(x[1]), reverse=True
    )[:8]:
        dominant_type = Counter(i.get("type", "unknown") for i in cluster).most_common(1)[0][0]
        risk_zones.append({
            "lat": lat,
            "lon": lon,
            "incident_count": len(cluster),
            "dominant_type": dominant_type,
            "risk_level": (
                "critical" if len(cluster) > 6 else
                "high"     if len(cluster) > 3 else
                "medium"
            ),
        })

    # ── Type distribution ───────────────────────────────────────────
    type_distribution = dict(type_counts)

    return {
        "hotspot_hours": hotspot_hours,
        "trend": trend,
        "daily_averages": daily_avgs,
        "risk_zones": risk_zones,
        "hourly_timeline": hotspot_hours,  # alias for chart
        "type_distribution": type_distribution,
    }
