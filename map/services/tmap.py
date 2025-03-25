import requests
from django.conf import settings

def get_pedestrian_route(startX, startY, endX, endY):
    url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1"
    headers = {
        "Content-Type": "application/json",
        "appKey": settings.TMAP_API_KEY
    }
    body = {
        "startX": str(startX),
        "startY": str(startY),
        "endX": str(endX),
        "endY": str(endY),
        "startName": "출발지", 
        "endName": "도착지",  
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO"
    }

    response = requests.post(url, headers=headers, json=body)

    print("📍 Tmap 요청 결과 코드:", response.status_code)
    print("📍 Tmap 응답 내용:", response.text)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.text}
