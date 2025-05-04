import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from .models import TrafficLight
from .serializers import TrafficLightSerializer
from math import radians, cos, sin, sqrt, atan2
from urllib.parse import quote

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

class AllTrafficLightsView(APIView):
    def get(self, request):
        lights = TrafficLight.objects.all()
        serializer = TrafficLightSerializer(lights, many=True)
        return Response(serializer.data)

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
            if haversine(lat, lon, light.latitude, light.longitude) <= radius:
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

class TmapRouteView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        startX = request.query_params.get("startX")
        startY = request.query_params.get("startY")
        endX = request.query_params.get("endX")
        endY = request.query_params.get("endY")

        if not all([startX, startY, endX, endY]):
            return Response({"error": "Missing startX, startY, endX, or endY"}, status=400)

        headers = {
            "appKey": settings.TMAP_API_KEY,
            "Content-Type": "application/json"
        }

        url = "https://apis.openapi.sk.com/tmap/routes?version=1"
        body = {
            "startX": startX,
            "startY": startY,
            "endX": endX,
            "endY": endY,
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "searchOption": "0",
            "sort": "index"
        }

        try:
            routes = []
            for option in ["0", "1"]:
                body["searchOption"] = option
                response = requests.post(url, headers=headers, json=body, timeout=5)
                response.raise_for_status()
                data = response.json()
                routes.append({
                    "type": "recommended" if option == "0" else "alternative",
                    "route": data
                })
            return Response({"routes": routes})
        except requests.RequestException as e:
            return Response({"error": "TMAP API 요청 실패", "details": str(e)}, status=500)

class SegmentedRouteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        startX = request.query_params.get("startX")
        startY = request.query_params.get("startY")
        endX = request.query_params.get("endX")
        endY = request.query_params.get("endY")

        if not all([startX, startY, endX, endY]):
            return Response({"error": "Missing coordinates"}, status=400)

        user = request.user
        speed = user.min_speed or 1.0

        headers = {
            "appKey": settings.TMAP_API_KEY,
            "Content-Type": "application/json"
        }

        url = "https://apis.openapi.sk.com/tmap/routes?version=1"
        base_body = {
            "startX": startX,
            "startY": startY,
            "endX": endX,
            "endY": endY,
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "sort": "index"
        }

        results = []
        for option in ["0", "1"]:
            base_body["searchOption"] = option
            response = requests.post(url, headers=headers, json=base_body, timeout=5)
            if response.status_code != 200:
                continue
            tmap_data = response.json()
            coords = []
            for feature in tmap_data.get("features", []):
                if feature["geometry"]["type"] == "LineString":
                    coords.extend(feature["geometry"]["coordinates"])

            segments = []
            segment_number = 1
            start = coords[0]
            traffic_lights = TrafficLight.objects.all()

            for i in range(1, len(coords)):
                point = coords[i]
                dist = haversine(start[1], start[0], point[1], point[0])
                time_sec = dist / speed
                segment = {
                    "segment_number": segment_number,
                    "distance_m": round(dist, 2),
                    "estimated_time_sec": round(time_sec, 2),
                    "start": {"lat": start[1], "lng": start[0]},
                    "end": {"lat": point[1], "lng": point[0]},
                    "speed_used": speed
                }
                for light in traffic_lights:
                    if haversine(point[1], point[0], light.latitude, light.longitude) < 10:
                        segment["traffic_light"] = {
                            "lat": light.latitude,
                            "lng": light.longitude,
                            "name": light.name
                        }
                        segments.append(segment)
                        segment_number += 1
                        start = point
                        break

            results.append({
                "route_type": "recommended" if option == "0" else "alternative",
                "total_distance_m": round(sum(seg["distance_m"] for seg in segments), 2),
                "total_time_sec": round(sum(seg["estimated_time_sec"] for seg in segments), 2),
                "speed_used": speed,
                "total_segments": len(segments),
                "segments": segments
            })

        return Response({"routes": results})

class TmapSegmentedRouteView(SegmentedRouteView):
    def get(self, request):
        base_response = super().get(request)
        if base_response.status_code != 200:
            return base_response

        startX = request.query_params.get("startX")
        startY = request.query_params.get("startY")
        endX = request.query_params.get("endX")
        endY = request.query_params.get("endY")

        user = request.user
        speed = user.min_speed or 1.0

        headers = {
            "appKey": settings.TMAP_API_KEY,
            "Content-Type": "application/json"
        }

        url = "https://apis.openapi.sk.com/tmap/routes?version=1"
        base_body = {
            "startX": startX,
            "startY": startY,
            "endX": endX,
            "endY": endY,
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "sort": "index"
        }

        results = []
        for option in ["0", "1"]:
            base_body["searchOption"] = option
            response = requests.post(url, headers=headers, json=base_body, timeout=5)
            if response.status_code != 200:
                continue
            tmap_data = response.json()

            for route in base_response.data["routes"]:
                if (option == "0" and route["route_type"] == "recommended") or (option == "1" and route["route_type"] == "alternative"):
                    route["tmap_raw"] = tmap_data
                    results.append(route)

        return Response({"routes": results})