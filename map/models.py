from django.db import models

class TrafficLight(models.Model):
    itst_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return f"{self.itst_id} - {self.name}"