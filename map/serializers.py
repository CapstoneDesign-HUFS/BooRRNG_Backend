from rest_framework import serializers

class CoordinateSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()

class RouteRequestSerializer(serializers.Serializer):
    start = CoordinateSerializer()
    end = CoordinateSerializer()
