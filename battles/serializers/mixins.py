from datetime import datetime
from django.utils import timezone
from rest_framework import serializers
from croniter import croniter
from ..models import Battle

# ---- Helpers reutilizables ----

def next_run_from_cron(cron_expr: str, base_dt=None):
    """Devuelve el próximo datetime (aware, en la tz actual) para una expresión CRON de 5 campos."""
    if not cron_expr:
        return None
    base = base_dt or timezone.now()
    try:
        nxt = croniter(cron_expr, base).get_next(datetime)
        if timezone.is_naive(nxt):
            nxt = timezone.make_aware(nxt, timezone.get_current_timezone())
        return nxt
    except Exception:
        return None

def validate_cron_5(cron_str: str):
    """Valida que tenga 5 campos; lanza serializers.ValidationError si es inválida."""
    parts = (cron_str or "").split()
    if len(parts) != 5:
        raise serializers.ValidationError("CRON must have 5 fields (min hour dom mon dow)")
    return parts

# ---- Mixins de presentación / campos calculados ----

class StateFieldsMixin(serializers.Serializer):
    hp_a = serializers.SerializerMethodField()
    hp_b = serializers.SerializerMethodField()

    def get_hp_a(self, obj): return (obj.state or {}).get("hp_a")
    def get_hp_b(self, obj): return (obj.state or {}).get("hp_b")

class StatusPresentationMixin(serializers.Serializer):
    status_label = serializers.SerializerMethodField()
    status_badge = serializers.SerializerMethodField()

    def _effective_status(self, obj: Battle) -> str:
        s = obj.status
        if s != Battle.Status.RUNNING and getattr(obj, "scheduled_cron", None):
            # si hay cron y no está corriendo, lo tratamos como Programado
            s = Battle.Status.SCHEDULED
        return s

    def get_status_label(self, obj):
        effective = self._effective_status(obj)
        mapping = {
            Battle.Status.PENDING:   "Pendiente",
            Battle.Status.SCHEDULED: "Programado",
            Battle.Status.RUNNING:   "En ejecución",
            Battle.Status.FINISHED:  "Finalizado",
            Battle.Status.FAILED:    "Fallido",
        }
        # fallback al display del modelo si algo cambia
        return mapping.get(effective, obj.get_status_display())

    def get_status_badge(self, obj):
        effective = self._effective_status(obj)
        classes = {
            Battle.Status.FINISHED:  "positive",
            Battle.Status.FAILED:    "negative",
            Battle.Status.SCHEDULED: "info",
            Battle.Status.RUNNING:   "is-running",
            Battle.Status.PENDING:   "is-pending",
        }
        return classes.get(effective, "neutral")

class NextRunMixin(serializers.Serializer):
    next_run = serializers.SerializerMethodField()

    def get_next_run(self, obj):
        # Si el modelo ya expone next_run_at, úsalo
        dt = getattr(obj, "next_run_at", None)
        if dt is None and getattr(obj, "scheduled_cron", None):
            dt = next_run_from_cron(obj.scheduled_cron)
        if not dt:
            return None
        # Devuelve ISO en tz local del servidor (frontend lo mostrará en local del navegador)
        return timezone.localtime(dt).isoformat()
