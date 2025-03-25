from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.tmap import get_pedestrian_route

class TmapRouteView(APIView):
    def get(self, request):
        startX = request.query_params.get("startX")
        startY = request.query_params.get("startY")
        endX = request.query_params.get("endX")
        endY = request.query_params.get("endY")

        if not all([startX, startY, endX, endY]):
            return Response({"error": "모든 좌표값을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        result = get_pedestrian_route(startX, startY, endX, endY)

        # 실패했는지 확인하고 에러 반환
        if result.get("error"):
            return Response({"error": "Tmap API 호출 실패", "details": result.get("error")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_200_OK)
