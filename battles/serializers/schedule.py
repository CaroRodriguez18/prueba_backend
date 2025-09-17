from rest_framework import serializers
from celery.schedules import crontab
from .mixins import validate_cron_5

class ScheduleSerializer(serializers.Serializer):
    """
    Para acción /schedule/:
    - cron vacío => desprogramar (battle -> PENDING)
    - cron con valor => valida CRON (5 campos)
    """
    cron = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Leave empty to create a pending battle. Use 5-part CRON syntax.",
    )

    def validate_cron(self, value):
        value = (value or "").strip()
        if value == "":
            return ""  # desprogramar
        minute, hour, dom, moy, dow = validate_cron_5(value)
        try:
            crontab(minute=minute, hour=hour, day_of_month=dom, month_of_year=moy, day_of_week=dow)
        except Exception:
            raise serializers.ValidationError("Invalid CRON expression")
        return value
