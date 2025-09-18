from rest_framework import serializers
from django.utils import timezone
from celery.schedules import crontab
from ..models import Battle
from .mixins import (
    StateFieldsMixin, StatusPresentationMixin, NextRunMixin,
    validate_cron_5
)


class BattleBaseSerializer(serializers.ModelSerializer):
    pokemon_a_name = serializers.ReadOnlyField(source="pokemon_a.name")
    pokemon_b_name = serializers.ReadOnlyField(source="pokemon_b.name")
    scenario_name  = serializers.ReadOnlyField(source="scenario.name")
    winner_name    = serializers.ReadOnlyField(source="winner.name")

    class Meta:
        model = Battle
        fields = [
            "id",
            "pokemon_a", "pokemon_a_name",
            "pokemon_b", "pokemon_b_name",
            "scenario", "scenario_name",
            "scheduled_cron",
            "status", "winner", "winner_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["status", "winner", "created_at", "updated_at"]

# ---- LISTA: ligera (para cards) ----

class BattleListSerializer(BattleBaseSerializer,
                           StatusPresentationMixin,
                           StateFieldsMixin,
                           NextRunMixin):
    class Meta(BattleBaseSerializer.Meta):
        fields = BattleBaseSerializer.Meta.fields + [
            "status_label", "status_badge",
            "hp_a", "hp_b",
            "next_run",
        ]

# ---- DETALLE: incluye log y state completo ----

class BattleDetailSerializer(BattleBaseSerializer,
                             StatusPresentationMixin,
                             StateFieldsMixin,
                             NextRunMixin):
    class Meta(BattleBaseSerializer.Meta):
        fields = BattleBaseSerializer.Meta.fields + [
            "log", "state",
            "status_label", "status_badge",
            "hp_a", "hp_b",
            "next_run",
        ]
        read_only_fields = BattleBaseSerializer.Meta.read_only_fields + ["log", "state"]

# ---- WRITE: creación/edición (sin campos de solo lectura) ----

class BattleWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Battle
        fields = [
            "id",
            "pokemon_a", "pokemon_b", "scenario",
            "scheduled_cron",
        ]

    def validate(self, attrs):
        a = attrs.get("pokemon_a") or getattr(self.instance, "pokemon_a", None)
        b = attrs.get("pokemon_b") or getattr(self.instance, "pokemon_b", None)
        if a and b and a.id == b.id:
            raise serializers.ValidationError({"pokemon_b": "pokemon_b must be different from pokemon_a"})
        return attrs

    def validate_scheduled_cron(self, value):
        if not value:
            return value
        minute, hour, dom, moy, dow = validate_cron_5(value)
        try:
            crontab(minute=minute, hour=hour, day_of_month=dom, month_of_year=moy, day_of_week=dow)
        except Exception:
            raise serializers.ValidationError("Invalid CRON expression")
        return value
