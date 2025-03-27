import requests
import os
from dotenv import load_dotenv
from pyproj import Transformer
from math import radians, cos, sin, sqrt, atan2

load_dotenv()
API_KEY = os.getenv("SEOUL_API_KEY")

# TM -> WGS84 좌표 변환
def convert_tm_to_wgs84(x, y):
    transformer = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(x, y)
    return lon, lat

# 반경 기준 필터링
def is_within_radius(lat1, lon1, lat2, lon2, radius_m=100):
    R = 6371000  
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance <= radius_m

# 신호등 데이터 전체 조회
def fetch_traffic_lights(start_index=1, end_index=1000):
    url = f"http://openapi.seoul.go.kr:8088/{API_KEY}/json/trafficSafetyA057PInfo/{start_index}/{end_index}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("신호등 API 호출 실패")
    data = response.json()
    return data.get("trafficSafetyA057PInfo", {}).get("row", [])

# 중심 좌표 기준 반경 내 신호등 필터링 
def get_nearby_traffic_lights(center_lat, center_lon, radius=100, start_index=1, end_index=1000):
    all_lights = fetch_traffic_lights(start_index, end_index)
    nearby_lights = []

    for light in all_lights:
        try:
            tm_x = float(light["XCRD"])
            tm_y = float(light["YCRD"])
            lon, lat = convert_tm_to_wgs84(tm_x, tm_y)

            if is_within_radius(center_lat, center_lon, lat, lon, radius):
                nearby_lights.append({
                    "id": light.get("ATCH_MNG_NO1"),
                    "kind": light.get("TRFC_LGHT_KND"),
                    "count": light.get("TRFC_LGHT_CNT"),
                    "direction": light.get("ATCH_DRCT"),
                    "x": lon,
                    "y": lat
                })
        except (KeyError, ValueError, TypeError):
            continue

    return nearby_lights
