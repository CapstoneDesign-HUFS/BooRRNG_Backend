import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import TrafficLight
from .serializers import TrafficLightSerializer
from math import radians, cos, sin, sqrt, atan2
from rest_framework.permissions import AllowAny
from urllib.parse import quote


# Haversine 거리 계산 함수 (m 단위)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# 전체 신호등 위치
class AllTrafficLightsView(APIView):
    def get(self, request):
        lights = TrafficLight.objects.all()
        serializer = TrafficLightSerializer(lights, many=True)
        return Response(serializer.data)

# 반경 내 신호등 위치
class NearbyTrafficLightsView(APIView):
    def get(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lon = float(request.query_params.get('lon'))
        except (TypeError, ValueError):
            return Response({"error": "Invalid or missing 'lat' and 'lon' parameters."}, status=400)

        radius = float(request.query_params.get('radius', 500))  
        nearby_lights = []
        for light in TrafficLight.objects.all():
            distance = haversine(lat, lon, light.latitude, light.longitude)
            if distance <= radius:
                nearby_lights.append(light)

        serializer = TrafficLightSerializer(nearby_lights, many=True)
        return Response(serializer.data)
class V2XSignalTestView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        base_url = "https://t-data.seoul.go.kr/apig/apiman-gateway/tapi/v2xSignalPhaseTimingInformation/1.0"
        encoded_key = quote(settings.V2X_API_KEY, safe='')

        page = request.query_params.get("pageNo", "1")
        rows = request.query_params.get("numOfRows", "10")
        itst_id = request.query_params.get("itstId")  

        params = {
            "apiKey": encoded_key,
            "type": "json",
            "pageNo": page,
            "numOfRows": rows,
        }

        if itst_id:
            params["itstId"] = itst_id

        try:
            response = requests.get(base_url, params=params, timeout=5)
            response.raise_for_status()
            return Response(response.json())
        except requests.RequestException as e:
            return Response({"error": "Failed to fetch V2X data", "details": str(e)}, status=500)
