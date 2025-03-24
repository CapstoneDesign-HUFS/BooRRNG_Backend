from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import OutstandingToken, BlacklistedToken
from .serializers import SignupSerializer, LoginSerializer, UserInfoSerializer, UserEditSerializer
from .models import SpeedRecommendation

class SignupView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'password': user.password,
                    'nickname': user.nickname,
                    'birthdate': user.birthdate,
                    'gender': user.gender,
                    'agreed_terms': user.agreed_terms
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'nickname': user.nickname,
                    'password': user.password
                }
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            tokens = OutstandingToken.objects.filter(user=request.user)
            for token in tokens:
                BlacklistedToken.objects.get_or_create(token=token)
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Logout failed."}, status=status.HTTP_400_BAD_REQUEST)

class UserInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserInfoSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserEditView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        serializer = UserEditSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response_serializer = UserInfoSerializer(request.user)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VelocityRecommendationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        age = user.calculate_age()

        # 나이 → age_group 매핑
        if age < 10:
            age_group = 0
        elif age < 20:
            age_group = 10
        elif age < 30:
            age_group = 20
        elif age < 40:
            age_group = 30
        elif age < 50:
            age_group = 40
        elif age < 60:
            age_group = 50
        else:
            age_group = 60

        try:
            recommendation = SpeedRecommendation.objects.get(age_group=age_group, gender=user.gender)
            return Response({
                "recommendations": {
                    "slow": recommendation.slow,
                    "normal": recommendation.normal,
                    "fast": recommendation.fast,
                }
            }, status=status.HTTP_200_OK)
        except SpeedRecommendation.DoesNotExist:
            return Response({"error": "Speed recommendation not found."}, status=status.HTTP_404_NOT_FOUND)
