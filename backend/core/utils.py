# core/utils.py
import datetime
import math


def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def sigmoid(x: float) -> float:
    # gentle calibration so 0.5± gets spread a bit
    return 1 / (1 + math.exp(-4 * (x - 0.5)))


def normalize_conf(score: float) -> float:
    # map raw score -> calibrated [0,1]
    return clamp01(sigmoid(score))


def jaccard(a: str, b: str) -> float:
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def haversine_m(lat1, lon1, lat2, lon2):
    # metres; optional if you add geo later
    R = 6371000
    from math import radians, sin, cos, sqrt, atan2
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dl / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))
