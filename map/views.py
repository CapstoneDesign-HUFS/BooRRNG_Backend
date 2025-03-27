from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.tmap import get_pedestrian_route
from .services.traffic_light import fetch_traffic_lights, convert_tm_to_wgs84, is_within_radius

class TmapRouteView(APIView):
    def get(self, request):
        startX = request.query_params.get("startX")
        startY = request.query_params.get("startY")
        endX = request.query_params.get("endX")
        endY = request.query_params.get("endY")

        if not all([startX, startY, endX, endY]):
            return Response({"error": "모든 좌표값을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        result = get_pedestrian_route(startX, startY, endX, endY)

        if result.get("error"):
            return Response({"error": "Tmap API 호출 실패", "details": result.get("error")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_200_OK)

class TrafficLightView(APIView):
    def get(self, request):
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        radius = float(request.query_params.get("radius", 100))

        if not lat or not lon:
            return Response({"error": "lat, lon 값을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        center_lat = float(lat)
        center_lon = float(lon)

        raw_data = fetch_traffic_lights()
        result = []

        for row in raw_data:
            try:
                tm_x = float(row.get("XCRD"))
                tm_y = float(row.get("YCRD"))
                lon_, lat_ = convert_tm_to_wgs84(tm_x, tm_y)

                if is_within_radius(center_lat, center_lon, lat_, lon_, radius):
                    result.append({
                        "id": row.get("ATCH_MNG_NO1"),
                        "kind": row.get("TRFC_LGHT_KND"),
                        "count": row.get("TRFC_LGHT_CNT"),
                        "direction": row.get("ATCH_DRCT"),
                        "x": lon_,
                        "y": lat_
                    })
            except:
                continue

        return Response({"total": len(result), "lights": result}, status=status.HTTP_200_OK)
