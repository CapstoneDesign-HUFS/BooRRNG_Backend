import os
import pandas as pd
import requests
import json
import csv
from pathlib import Path
from datetime import datetime, timezone
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from haversine import haversine
from .models import TrafficLight
from .serializers import TrafficLightSerializer
from math import radians, cos, sin, sqrt, atan2
from urllib.parse import quote

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
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
        api_key = settings.V2X_API_KEY  
        page = request.query_params.get("pageNo", "1")
        rows = request.query_params.get("numOfRows", "10")
        itst_id = request.query_params.get("itstId")

        params = {
            "apikey": api_key,  
            "type": "json",
            "pageNo": page,
            "numOfRows": rows,
        }
        if itst_id:
            params["itstId"] = itst_id

        try:
            response = requests.get(base_url, params=params, timeout=20)
            print("요청 URL:", response.request.url) 
            response.raise_for_status()
            return Response(response.json())
        except requests.Timeout:
            return Response({"error": "요청 시간이 초과되었습니다."}, status=504)
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

        # 도보 경로 URL
        url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1"

        try:
            routes = []

            for option in ["0", "10"]:  
                body = {
                    "startX": startX,
                    "startY": startY,
                    "endX": endX,
                    "endY": endY,
                    "reqCoordType": "WGS84GEO",
                    "resCoordType": "WGS84GEO",
                    "startName": "출발지",
                    "endName": "도착지",
                    "searchOption": option  
                }

                response = requests.post(url, headers=headers, json=body, timeout=5)
                response.raise_for_status()

                try:
                    cleaned_text = response.text.replace('\x00', '') 
                    data = json.loads(cleaned_text) 
                except json.JSONDecodeError as e:
                    return Response({"error": "Invalid JSON response from TMAP", "details": str(e)}, status=500)

                route_type = "recommended" if option == "0" else "alternative"
                routes.append({
                    "type": route_type,
                    "route": data
                })

            return Response({"routes": routes})

        except requests.RequestException as e:
            return Response({"error": "TMAP 도보 경로 요청 실패", "details": str(e)}, status=500)

class SegmentedRouteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
            startX = request.query_params.get("startX")
            startY = request.query_params.get("startY")
            endX = request.query_params.get("endX")
            endY = request.query_params.get("endY")

            if not all([startX, startY, endX, endY]):
                return Response({"error": "Missing coordinates"}, status=400)
            
            try:
                response = requests.get("http://127.0.0.1:8000/member/info/")
                response.raise_for_status()
                user_data = response.json()
                speed = user_data.get("min_speed", 1.0)  
            except (requests.RequestException, KeyError):
                speed = 1.0  

            headers = {
                "appKey": settings.TMAP_API_KEY,
                "Content-Type": "application/json"
            }

            url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1"
            
            def create_body(route_type):
                return {
                    "startX": startX,
                    "startY": startY,
                    "endX": endX,
                    "endY": endY,
                    "reqCoordType": "WGS84GEO",
                    "resCoordType": "WGS84GEO",
                    "startName": "출발지",
                    "endName": "도착지",
                    "searchOption": "0" if route_type == "recommended" else "10"  
                }

            def create_segment(segment_number, start_point, end_point, distance, time, light=None):
                return {
                    "segment_number": segment_number,
                    "distance_m": round(distance, 2),
                    "estimated_time_sec": round(time, 2),
                    "start": {"lat": start_point[1], "lng": start_point[0]},
                    "end": {"lat": end_point[1], "lng": end_point[0]},
                    "speed_used": speed,  
                    "traffic_light": light
                }

            def process_route(route_type):
                body = create_body(route_type)
                try:
                    response = requests.post(url, headers=headers, json=body, timeout=5)
                    response.raise_for_status()
                    tmap_data = json.loads(response.text.replace('\x00', ''))

                    if "features" not in tmap_data:
                        return {"error": f"No features found for {route_type} route"}

                    traffic_lights = TrafficLight.objects.all()
                    coords = []
                    segments = []
                    segment_number = 1
                    total_distance = 0
                    total_time = 0
                    segment_start = None

                    for feature in tmap_data.get("features", []):
                        geometry = feature.get("geometry", {})
                        properties = feature.get("properties", {})
                        description = properties.get("description", "")

                        if geometry.get("type") == "Point":
                            point = geometry.get("coordinates")
                            coords.append(point)
                        elif geometry.get("type") == "LineString":
                            line_coords = geometry.get("coordinates", [])
                            coords.extend(line_coords)

                        if "횡단보도" in description or "건널목" in description or "교차로" in description:
                            min_distance = float('inf')
                            closest_light = None
                            for light in traffic_lights:
                                dist = haversine(point[1], point[0], light.latitude, light.longitude)
                                if dist < min_distance:
                                    min_distance = dist
                                    closest_light = {
                                        "lat": light.latitude,
                                        "lng": light.longitude,
                                        "name": light.name
                                    }

                            if segment_start is None:
                                segment_start = coords[0]
                            segment_end = coords[-1]

                            segment = create_segment(segment_number, segment_start, segment_end, total_distance, total_time, closest_light)
                            segments.append(segment)
                            segment_number += 1

                            segment_start = segment_end

                    if segment_start:
                        segment = create_segment(segment_number, segment_start, coords[-1], total_distance, total_time)
                        segments.append(segment)

                    return {
                        "route_type": route_type,
                        "total_distance_m": round(total_distance, 2),
                        "total_time_sec": round(total_time, 2),
                        "speed_used": 1.0,
                        "total_segments": len(segments),
                        "segments": segments
                    }

                except requests.RequestException as e:
                    return {"error": f"TMAP {route_type} 경로 요청 실패", "details": str(e)}

            recommended_route = process_route("recommended")
            alternative_route = process_route("alternative")

            response_data = {"routes": []}
            if "error" not in recommended_route:
                response_data["routes"].append(recommended_route)
            if "error" not in alternative_route:
                response_data["routes"].append(alternative_route)

            return Response(response_data)
class TmapSegmentedRouteView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        startX = request.query_params.get("startX")
        startY = request.query_params.get("startY")
        endX = request.query_params.get("endX")
        endY = request.query_params.get("endY")

        if not all([startX, startY, endX, endY]):
            return Response({"error": "Missing coordinates"}, status=400)

        try:
            response = requests.get("http://127.0.0.1:8000/member/info/")
            response.raise_for_status()
            user_data = response.json()
            speed = user_data.get("min_speed", 1.0)  
        except (requests.RequestException, KeyError):
            speed = 1.0  

        headers = {
            "appKey": settings.TMAP_API_KEY,
            "Content-Type": "application/json"
        }

        url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1"
        
        def create_body(route_type):
            return {
                "startX": startX,
                "startY": startY,
                "endX": endX,
                "endY": endY,
                "reqCoordType": "WGS84GEO",
                "resCoordType": "WGS84GEO",
                "startName": "출발지",
                "endName": "도착지",
                "searchOption": "0" if route_type == "recommended" else "10"  
            }

        def create_segment(segment_number, start_point, end_point, distance, time, light=None):
            return {
                "segment_number": segment_number,
                "distance_m": round(distance, 2),
                "estimated_time_sec": round(time, 2),
                "start": {"lat": start_point[1], "lng": start_point[0]},
                "end": {"lat": end_point[1], "lng": end_point[0]},
                "speed_used": speed,  
                "traffic_light": light
            }

        def process_route(route_type):
            body = create_body(route_type)
            try:
                response = requests.post(url, headers=headers, json=body, timeout=5)
                response.raise_for_status()
                tmap_data = json.loads(response.text.replace('\x00', ''))

                if "features" not in tmap_data:
                    return {"error": f"No features found for {route_type} route"}

                segments = []
                segment_number = 1

                for feature in tmap_data.get("features", []):
                    geometry = feature.get("geometry", {})
                    properties = feature.get("properties", {})
                    description = properties.get("description", "")

                    # ✅ 1. LineString만 세그먼트 처리
                    if geometry.get("type") != "LineString":
                        continue

                    line_coords = geometry.get("coordinates", [])
                    if not line_coords or len(line_coords) < 2:
                        continue

                    segment_start = line_coords[0]
                    segment_end = line_coords[-1]

                    # ✅ 2. start == end 세그먼트는 스킵
                    if segment_start == segment_end:
                        continue

                    segment_distance = properties.get("distance", 0)
                    segment_time = properties.get("time", 0)

                    # ✅ 3. 교차로/횡단보도 포함 여부 → 추후 보행자 신호 매핑용 (지금은 None)
                    traffic_light = None

                    if "횡단보도" in description or "건널목" in description or "교차로" in description:
                        # traffic_light 매핑 로직은 추후 추가
                        traffic_light = {"hint": "TODO: 보행자 신호 매핑 필요"}

                    segments.append(
                        create_segment(segment_number, segment_start, segment_end, segment_distance, segment_time, traffic_light)
                    )
                    segment_number += 1

                total_distance = sum(seg["distance_m"] for seg in segments)
                total_time = sum(seg["estimated_time_sec"] for seg in segments)

                return {
                    "route_type": route_type,
                    "total_distance_m": round(total_distance, 2),
                    "total_time_sec": round(total_time, 2),
                    "speed_used": speed,
                    "total_segments": len(segments),
                    "segments": segments,
                    "tmap_raw": tmap_data
                }

            except requests.RequestException as e:
                return {"error": f"TMAP {route_type} 경로 요청 실패", "details": str(e)}

        recommended_route = process_route("recommended")
        alternative_route = process_route("alternative")

        response_data = {"routes": []}
        if "error" not in recommended_route:
            response_data["routes"].append(recommended_route)
        if "error" not in alternative_route:
            response_data["routes"].append(alternative_route)
            
        return Response(response_data)

class SignalStatusView(APIView):
    def get(self, request):
        its_id = request.query_params.get("itsId")
        if not its_id:
            return Response({"error": "Missing 'itsId' parameter"}, status=status.HTTP_400_BAD_REQUEST)

        # API 호출
        url = "https://t-data.seoul.go.kr/apig/apiman-gateway/tapi/v2xSignalPhaseTimingFusionInformation/1.0"
        headers = {"accept": "application/json"}
        params = {"apikey": quote(settings.V2X_API_KEY, safe='')}

        try:
            response = requests.get(url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            return Response({"error": "API 호출 중 오류가 발생했습니다.", "details": str(e)}, status=500)

        # 해당 교차로 데이터 찾기
        item = next((x for x in data if str(x.get("itstId", "")).strip() == str(its_id)), None)
        if not item:
            return Response({"error": "ITS ID에 해당하는 데이터를 찾을 수 없습니다."}, status=404)

        # 교차로 이름 가져오기
        csv_path = Path(__file__).resolve().parent / "data" / "location.csv"
        intersection_name = None
        try:
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("itstId", "").strip() == str(its_id):
                        intersection_name = row.get("itstNm", "").strip()
                        break
        except Exception as e:
            print(f"[WARN] 교차로 이름 조회 실패: {e}")

        directions = ["nt", "et", "st", "wt", "ne", "nw", "se", "sw"]

        signals = []

        for key in directions:
            status_key = f"{key}PdsgStatNm"
            time_key = f"{key}PdsgRmdrCs"
            raw_status = item.get(status_key)
            remaining_raw = item.get(time_key)

            seconds = round(remaining_raw / 10, 1) if remaining_raw is not None else None

            if raw_status:
                raw_status_lower = raw_status.lower()
                if "stop" in raw_status_lower:
                    color = "red"
                elif "protected" in raw_status_lower:
                    color = "green"
                elif "permissive" in raw_status_lower:
                    # permissive green + 5초 미만이면 'red' 처리
                    if seconds is not None and seconds < 5:
                        color = "Hurry up!"
                    else:
                        color = "green"
                else:
                    color = None
            else:
                color = None

            
            signals.append({
                "direction": key,
                "signalColor": color,
                "remainingSeconds": seconds
            })
        
        result = {
            "intersectionName": intersection_name,
            "timestamp": datetime.fromtimestamp(item["trsmUtcTime"] / 1000, tz=timezone.utc).isoformat(),
            "signals": signals
        }

        return Response(result, status=200)

def calculate_crossing_delay(signal_status, arrival_time_sec):
    """
    특정 교차로에서 도착 시간에 따라 대기시간 계산용 함수
    아래 총 소요시간 계산을 위한 함수임임
    - signal_status: SignalStatusView API 결과 (signals 포함)
    - arrival_time_sec: 누적 도착 시간 (초)
    """
    signal_cycle = {
        "서울중랑우체국": {"green": 41, "red": 110},
        # 첫 번째 교차로인 동일로지하차도앞은 측정 후 추가
    }

    intersection_name = signal_status.get("intersectionName")
    signals = signal_status.get("signals", [])

    if not intersection_name or intersection_name not in signal_cycle:
        return 0  # 주기 정보 없으면 계산 스킵

    green_dur = signal_cycle[intersection_name]["green"]
    red_dur = signal_cycle[intersection_name]["red"]

    # 신호 상태 추출
    signal_color = None
    remaining = None
    for s in signals:
        if s["signalColor"] in ["green", "red"]:
            signal_color = s["signalColor"]
            remaining = s["remainingSeconds"]
            break

    if signal_color is None or remaining is None:
        return 0

    if signal_color == "green" and remaining >= arrival_time_sec:
        return 0  # 바로 통과

    wait_time = (remaining if signal_color == "red" else 0) + green_dur
    return wait_time

class RouteEstimatedTimeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        startX = request.query_params.get("startX")
        startY = request.query_params.get("startY")
        endX = request.query_params.get("endX")
        endY = request.query_params.get("endY")
        user_speed = 5 * 1000 / 3600  # 5km/h → 1.39 m/s

        if not all([startX, startY, endX, endY]):
            return Response({"error": "Missing coordinates"}, status=400)

        tmap_response = self.get_tmap_route(startX, startY, endX, endY)
        if "error" in tmap_response:
            return Response(tmap_response, status=500)

        all_coords = tmap_response["all_coords"]
        crossings = tmap_response["crossings"]
        original_tmap_time = tmap_response["total_time_sec"]

        # 교차로 기준 세그먼트 나누기
        segments = self.create_segments(all_coords, crossings)

        # 교차로 신호 조회
        signal_status_list = self.get_signal_status_list(crossings)

        # 예상 소요시간 계산
        result = self.calculate_total_expected_time(segments, signal_status_list, user_speed)

        return Response({
            "original_tmap_time_sec": original_tmap_time,
            "adjusted_time_sec": result["adjusted_total_time_sec"],
            "delays": result["delays"],
            "total_distance_m": result["total_distance_m"]
        })

    def get_tmap_route(self, startX, startY, endX, endY):
        url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1"
        headers = {
            "appKey": settings.TMAP_API_KEY,
            "Content-Type": "application/json"
        }

        body = {
            "startX": startX,
            "startY": startY,
            "endX": endX,
            "endY": endY,
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "startName": "출발지",
            "endName": "도착지",
            "searchOption": "0"
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=5)
            response.raise_for_status()
            tmap_data = json.loads(response.text.replace('\x00', ''))

            if "features" not in tmap_data:
                return {"error": "Tmap features not found"}

            all_coords = []
            crossings = []
            total_time_sec = 0

            for feature in tmap_data.get("features", []):
                geometry = feature.get("geometry", {})
                properties = feature.get("properties", {})
                description = properties.get("description", "")

                if geometry.get("type") == "LineString":
                    line_coords = geometry.get("coordinates", [])
                    all_coords.extend(line_coords)
                    total_time_sec += properties.get("time", 0)

                if geometry.get("type") == "Point" and any(kw in description for kw in ["횡단보도", "건널목", "교차로"]):
                    point = geometry.get("coordinates")
                    crossings.append({"lat": point[1], "lng": point[0], "description": description})

            return {
                "all_coords": all_coords,
                "crossings": crossings,
                "total_time_sec": total_time_sec
            }

        except requests.RequestException as e:
            return {"error": f"Tmap API 호출 실패: {str(e)}"}

    def create_segments(self, all_coords, crossings):
        segments = []
        segment_number = 1

        # 출발 ~ 첫 번째 교차로
        segment_points = []
        crossing_idx = 0
        last_idx = 0

        for i, point in enumerate(all_coords):
            segment_points.append(point)
            if crossing_idx < len(crossings):
                cross = crossings[crossing_idx]
                dist = haversine(point[1], point[0], cross["lat"], cross["lng"])
                if dist < 30:
                    segments.append({
                        "segment_number": segment_number,
                        "start": {"lat": segment_points[0][1], "lng": segment_points[0][0]},
                        "end": {"lat": point[1], "lng": point[0]},
                        "distance_m": self.calculate_distance(segment_points),
                        "description": cross["description"]
                    })
                    segment_number += 1
                    segment_points = [point]
                    crossing_idx += 1
            last_idx = i

        # 마지막 구간
        if segment_points:
            segments.append({
                "segment_number": segment_number,
                "start": {"lat": segment_points[0][1], "lng": segment_points[0][0]},
                "end": {"lat": segment_points[-1][1], "lng": segment_points[-1][0]},
                "distance_m": self.calculate_distance(segment_points),
                "description": "도착지"
            })

        return segments

    def calculate_distance(self, points):
        total = 0
        for i in range(len(points) - 1):
            total += haversine(points[i][1], points[i][0], points[i+1][1], points[i+1][0])
        return total

    def get_signal_status_list(self, crossings):
        signal_status_list = []
        csv_path = Path(__file__).resolve().parent / "data" / "location.csv"

        intersections = []
        try:
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    intersections.append({
                        "itstId": row.get("itstId"),
                        "name": row.get("itstNm"),
                        "lat": float(row.get("mapCtptIntLat")),
                        "lng": float(row.get("mapCtptIntLot"))
                    })
        except Exception as e:
            print(f"[ERROR] 교차로 CSV 로드 실패: {e}")
            return signal_status_list

        for cross in crossings:
            min_distance = float("inf")
            closest = None
            for intersection in intersections:
                dist = haversine(cross["lat"], cross["lng"], intersection["lat"], intersection["lng"])
                if dist < min_distance:
                    min_distance = dist
                    closest = intersection

            if closest and min_distance < 30:
                try:
                    response = requests.get(
                        "http://127.0.0.1:8000/map/traffic-lights/signal-status/",
                        params={"itsId": closest["itstId"]},
                        timeout=5
                    )
                    response.raise_for_status()
                    signal_status = response.json()
                    signal_status_list.append(signal_status)
                except requests.RequestException as e:
                    signal_status_list.append({
                        "error": f"Failed to fetch signal status for {closest['name']} (itstId: {closest['itstId']})"
                    })
            else:
                signal_status_list.append({
                    "error": f"No matching intersection found for crossing at ({cross['lat']}, {cross['lng']})"
                })

        return signal_status_list

    def calculate_total_expected_time(self, segments, signal_status_list, user_speed_mps):
        total_time = 0
        total_distance = 0
        delays = []

        for i, segment in enumerate(segments):
            segment_distance = segment["distance_m"]
            segment_time = segment_distance / user_speed_mps
            total_distance += segment_distance
            total_time += segment_time

            if i < len(signal_status_list):
                signal_status = signal_status_list[i]
                if "error" not in signal_status:
                    crossing_delay = calculate_crossing_delay(signal_status, total_time)
                    delays.append({
                        "intersection": signal_status.get("intersectionName", "Unknown"),
                        "delay_sec": round(crossing_delay, 2)
                    })
                    total_time += crossing_delay
                else:
                    delays.append({
                        "intersection": "Unknown",
                        "delay_sec": 0,
                        "error": signal_status["error"]
                    })

        return {
            "total_distance_m": round(total_distance, 2),
            "adjusted_total_time_sec": round(total_time, 2),
            "delays": delays
        }