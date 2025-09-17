from django.db import models

class Scenario(models.Model):
    name = models.CharField(max_length=100, unique=True)
    attack_modifier  = models.FloatField(default=1.0)
    defense_modifier = models.FloatField(default=1.0)
    speed_modifier   = models.FloatField(default=1.0)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ("id",)
