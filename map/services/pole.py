import pandas as pd
import os
from math import radians, cos, sin, sqrt, atan2
from pyproj import Transformer

# TM -> WGS84 변환기 초기화
transformer = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)

# CSV 파일
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'A057_L.csv')

def convert_tm_to_wgs84(x, y):
    lon, lat = transformer.transform(x, y)
    return lon, lat

def is_within_radius(lat1, lon1, lat2, lon2, radius_m=100):
    R = 6371000  # 지구 반지름 (m)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance <= radius_m

def get_nearby_poles(center_lat, center_lon, radius=100):
    df = pd.read_csv(CSV_PATH, encoding="utf-8")

    result = []
    for _, row in df.iterrows():
        try:
            x = float(row["X좌표"])
            y = float(row["Y좌표"])
            lon, lat = convert_tm_to_wgs84(x, y)

            if is_within_radius(center_lat, center_lon, lat, lon, radius):
                result.append({
                    "id": row["부착대관리번호"],
                    "irek_id": row["이력ID"],
                    "direction": row["부착대방향"],
                    "x": lon,
                    "y": lat
                })
        except Exception:
            continue

    return result
