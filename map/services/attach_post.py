import csv
import os
from pyproj import Transformer
from math import radians, cos, sin, sqrt, atan2

# TM -> WGS84 변환기 초기화 (EPSG:5186 -> 4326)
transformer = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)

def convert_tm_to_wgs84(x, y):
    lon, lat = transformer.transform(x, y)
    return lon, lat

def is_within_radius(lat1, lon1, lat2, lon2, radius_m=100):
    R = 6371000  
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance <= radius_m

def load_attach_post_data(center_lat, center_lon, radius=100, file_path="A057_L.csv"):
    result = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                x = float(row["X좌표"])
                y = float(row["Y좌표"])
                lon, lat = convert_tm_to_wgs84(x, y)

                if is_within_radius(center_lat, center_lon, lat, lon, radius):
                    result.append({
                        "id": row["부착대관리번호"],
                        "history_id": row["이력ID"],
                        "x": lon,
                        "y": lat,
                        "direction": row["부착대방향"]
                    })
            except:
                continue
    return result
