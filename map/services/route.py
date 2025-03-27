from geopy.distance import geodesic

def calculate_recommended_route(start, end):
    total_distance = geodesic((start['lat'], start['lng']), (end['lat'], end['lng'])).meters

    recommended_speed = 1.2
    estimated_time = total_distance / recommended_speed

    segment = {
        "segment_number": 1,
        "start": start,
        "end": end,
        "distance_m": round(total_distance, 2),
        "duration_sec": round(estimated_time),
        "recommended_speed_mps": recommended_speed,
        "message": "신호등 상황에 맞춰 이동 속도를 조절하세요"
    }

    return {
        "total_segments": 1,
        "segments": [segment]
    }
