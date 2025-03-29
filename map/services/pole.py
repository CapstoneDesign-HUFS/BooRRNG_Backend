from geopy.distance import geodesic
from datetime import datetime, timedelta
from map.services.v2x import get_signal_phase
from map.services.tmap import get_pedestrian_route
import pandas as pd
import os
from math import radians, cos, sin, sqrt, atan2
from pyproj import Transformer

# ----- 캐시된 신호등 CSV 로딩 -----
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'A057_L.csv')
poles_df = pd.read_csv(CSV_PATH, encoding="utf-8", low_memory=False)

transformer = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)

def convert_tm_to_wgs84(x, y):
    lon, lat = transformer.transform(x, y)
    return lon, lat

def is_within_radius(lat1, lon1, lat2, lon2, radius_m=100):
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c <= radius_m

def get_nearby_poles(center_lat, center_lon, radius=100):
    result = []
    for _, row in poles_df.iterrows():
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

def calculate_recommended_route(start, end, min_speed=1.0, max_speed=1.6):
    route_data = get_pedestrian_route(start['lng'], start['lat'], end['lng'], end['lat'])
    features = route_data.get("features", [])

    segments = []
    segment_number = 1
    prev_point = None

    for feature in features:
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates", [])
        geo_type = geometry.get("type")

        if geo_type != "LineString":
            continue

        for coord in coords:
            point = {"lat": coord[1], "lng": coord[0]}
            if prev_point is None:
                prev_point = point
                continue

            distance = geodesic((prev_point['lat'], prev_point['lng']), (point['lat'], point['lng'])).meters
            poles = get_nearby_poles(prev_point['lat'], prev_point['lng'], radius=15)
            is_traffic_light = len(poles) > 0

            if is_traffic_light:
                intersection_id = poles[0]['id']
                v2x_info = get_signal_phase(intersection_id)

                try:
                    first_phase = v2x_info['data']['data'][0]
                    cycle_duration = first_phase['cycle']['duration']
                    green_duration = first_phase['green']['duration']

                    duration = distance / max_speed
                    arrival_time = datetime.now() + timedelta(seconds=duration)
                    now = datetime.now()
                    elapsed = (arrival_time - now).total_seconds()
                    seconds_into_cycle = elapsed % cycle_duration
                    status = 'green' if seconds_into_cycle < green_duration else 'red'
                except:
                    status = 'unknown'

                segments.append({
                    "segment_number": segment_number,
                    "type": "신호등",
                    "start": prev_point,
                    "end": point,
                    "distance_m": round(distance, 2),
                    "duration_sec": round(distance / max_speed),
                    "recommended_speed_mps": round(max_speed, 2),
                    "arrival_signal_status": status,
                })
            else:
                avg_speed = (min_speed + max_speed) / 2
                duration = distance / avg_speed

                segments.append({
                    "segment_number": segment_number,
                    "type": "걷기",
                    "start": prev_point,
                    "end": point,
                    "distance_m": round(distance, 2),
                    "duration_sec": round(duration),
                    "recommended_speed_mps": round(avg_speed, 2),
                })

            prev_point = point
            segment_number += 1

    return {
        "total_segments": len(segments),
        "segments": segments
    }