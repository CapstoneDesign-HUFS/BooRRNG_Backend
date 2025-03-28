from rest_framework import serializers
from .models import User
from django.contrib.auth import authenticate

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

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        user = authenticate(email=email, password=password)
        if user is None:
            raise serializers.ValidationError("이메일 또는 비밀번호가 올바르지 않습니다.")
        data['user'] = user
        return data

class UserInfoSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'nickname', 'birthdate', 'gender',
            'age', 'agreed_terms', 'min_speed', 'max_speed'
        )

    def get_age(self, obj):
        return obj.calculate_age()

class UserEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('nickname', 'birthdate', 'gender', 'min_speed', 'max_speed')
