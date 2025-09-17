from django.db import models
from django.core.validators import MinValueValidator

class Pokemon(models.Model):
    name = models.CharField(max_length=100, unique=True)
    hp = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    attack = models.PositiveIntegerField()
    defense = models.PositiveIntegerField()
    speed = models.PositiveIntegerField()

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ("id",)
