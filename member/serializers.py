from rest_framework import serializers
from .models import User

class SignupSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'password1', 'password2', 'nickname', 'birthdate', 'gender', 'agreed_terms')
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data['password'] = validated_data.pop('password1')
        validated_data.pop('password2')
        return User.objects.create_user(**validated_data)