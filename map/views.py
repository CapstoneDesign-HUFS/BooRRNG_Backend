from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.tmap import get_pedestrian_route
from .services.traffic_light import fetch_traffic_lights, convert_tm_to_wgs84, is_within_radius
from .services.v2x import get_signal_phase
from .services.pole import get_nearby_poles
from .services.route import calculate_recommended_route
from .serializers import RouteRequestSerializer


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

class SignalPhaseView(APIView):
    def get(self, request):
        intersection_id = request.query_params.get("id")
        if not intersection_id:
            return Response({"error": "intersectionId를 입력해주세요"}, status=400)
        
        data = get_signal_phase(intersection_id)
        return Response(data, status=200)
    
class PoleView(APIView):
    def get(self, request):
        try:
            lat = float(request.query_params.get("lat"))
            lon = float(request.query_params.get("lon"))
            radius = float(request.query_params.get("radius", 100))
        except (TypeError, ValueError):
            return Response({"error": "lat, lon을 float 형식으로 전달해주세요."}, status=400)

        poles = get_nearby_poles(lat, lon, radius)
        return Response({"total": len(poles), "poles": poles}, status=200)

class RouteRecommendationView(APIView):
    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        if serializer.is_valid():
            start = serializer.validated_data['start']
            end = serializer.validated_data['end']

            print("start:", start)  
            print("end:", end)

            result = calculate_recommended_route(start=start, end=end)
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)