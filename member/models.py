from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from datetime import date

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=30)
    birthdate = models.DateField()
    gender = models.IntegerField()  # 1: male, 2: female
    agreed_terms = models.BooleanField(default=False)
    min_speed = models.FloatField(null=True, blank=True)
    max_speed = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nickname', 'birthdate', 'gender']

    def __str__(self):
        return self.email

    def calculate_age(self):
        today = date.today()
        return today.year - self.birthdate.year - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))

# SpeedRecommendation 모델
class SpeedRecommendation(models.Model):
    AGE_CHOICES = [
        (0, '10대 이하'),
        (10, '10대'),
        (20, '20대'),
        (30, '30대'),
        (40, '40대'),
        (50, '50대'),
        (60, '60대 이상'),
    ]

    GENDER_CHOICES = [
        (1, '남성'),
        (2, '여성'),
    ]

    age_group = models.IntegerField(choices=AGE_CHOICES)
    gender = models.IntegerField(choices=GENDER_CHOICES)
    slow = models.FloatField()
    normal = models.FloatField()
    fast = models.FloatField()

    class Meta:
        unique_together = ('age_group', 'gender')

    def __str__(self):
        return f'{self.age_group}대 - {"남성" if self.gender == 1 else "여성"}'

