import math
import requests
from django.http import JsonResponse
from django.conf import settings
from .models import SignalPole
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2)**2 + cos(phi1) * cos(phi2) * sin(dlambda / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def all_signal_poles(request):
    poles = SignalPole.objects.exclude(latitude__isnull=True, longitude__isnull=True)
    data = [{"id": p.pole_id, "latitude": p.latitude, "longitude": p.longitude} for p in poles]
    return JsonResponse(data, safe=False)

def nearby_signal_poles(request):
    lat = float(request.GET.get("latitude"))
    lon = float(request.GET.get("longitude"))
    radius = float(request.GET.get("radius", 500))
    result = []
    for pole in SignalPole.objects.exclude(latitude__isnull=True, longitude__isnull=True):
        dist = haversine(lat, lon, pole.latitude, pole.longitude)
        if dist <= radius:
            result.append({
                "id": pole.pole_id,
                "latitude": pole.latitude,
                "longitude": pole.longitude,
                "distance_m": round(dist, 2)
            })
    return JsonResponse(result, safe=False)

def nearest_signal_status(request):
    lat = float(request.GET.get("latitude"))
    lon = float(request.GET.get("longitude"))

    nearest = None
    min_dist = float('inf')

    for pole in SignalPole.objects.exclude(latitude__isnull=True, longitude__isnull=True):
        d = haversine(lat, lon, pole.latitude, pole.longitude)
        if d < min_dist:
            min_dist = d
            nearest = pole

    remaining_time = None
    status = None

    if nearest:
        try:
            api_url = "https://t-data.seoul.go.kr/apig/apiman-gateway/tapi/v2xSignalPhaseTimingInformation/1.0"
            response = requests.get(api_url, params={
                "apiKey": settings.V2X_API_KEY,
                "type": "json",
                "pageNo": 1,
                "numOfRows": 100
            }, headers={
                "User-Agent": "MyApp",
                "Accept": "application/json"
            }, timeout=5)

            data = response.json().get("data", [])
            for item in data:
                for key, value in item.items():
                    if key.endswith("RmdrCs") and value is not None:
                        remaining_time = value
                        status = "red" if value > 30 else "green"
                        break
                if remaining_time is not None:
                    break
        except Exception as e:
            print(f"[API ERROR] {e}")

    return JsonResponse({
        "id": nearest.pole_id if nearest else None,
        "distance_m": round(min_dist, 2) if nearest else None,
        "remaining_time": remaining_time,
        "signal_status": status
    })


def test_v2x_api(request):
    api_url = "https://t-data.seoul.go.kr/apig/apiman-gateway/tapi/v2xSignalPhaseTimingInformation/1.0"
    api_key = settings.V2X_API_KEY
    params = {
        "apiKey": api_key,
        "type": "json",
        "pageNo": request.GET.get("pageNo", "1"),
        "numOfRows": request.GET.get("numOfRows", "10")
    }
    headers = {
        "User-Agent": "MyApp",
        "Accept": "application/json"
    }

    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=5)
        return JsonResponse(response.json(), safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
