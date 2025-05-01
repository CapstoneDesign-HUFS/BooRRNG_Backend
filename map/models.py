from django.db import models

class TrafficLight(models.Model):
    light_id = models.CharField(max_length=50, unique=True)
    x = models.FloatField()
    y = models.FloatField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.light_id

class SignalPole(models.Model):
    pole_id = models.CharField(max_length=50, unique=True)
    direction = models.CharField(max_length=10, null=True, blank=True)
    x = models.FloatField()
    y = models.FloatField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.pole_id
