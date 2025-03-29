from geopy.distance import geodesic
from datetime import datetime, timedelta
from map.services.v2x import get_signal_phase
from map.services.pole import get_nearby_poles
from map.services.tmap import get_pedestrian_route


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
            continue  # Point 타입은 무시하고 LineString만 처리

        for coord in coords:
            point = {"lat": coord[1], "lng": coord[0]}
            if prev_point is None:
                prev_point = point
                continue

            distance = geodesic((prev_point['lat'], prev_point['lng']), (point['lat'], point['lng'])).meters

            # 신호등 존재 여부 판단
            poles = get_nearby_poles(prev_point['lat'], prev_point['lng'], radius=15)
            is_traffic_light = len(poles) > 0

            if is_traffic_light:
                # 신호등 구간 처리
                intersection_id = poles[0]['id']  
                v2x_info = get_signal_phase(intersection_id)

                try:
                    first_phase = v2x_info['data']['data'][0]
                    cycle_duration = first_phase['cycle']['duration']
                    green_duration = first_phase['green']['duration']
                    red_duration = first_phase['red']['duration']

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
                # 걷기 구간 처리
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
