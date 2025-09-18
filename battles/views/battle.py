from rest_framework.viewsets import ModelViewSet
from rest_framework.filters import SearchFilter
from ..models import Battle
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from ..serializers import (
    BattleListSerializer,
    BattleDetailSerializer,
    BattleWriteSerializer,
    ScheduleSerializer,
)
from ..tasks import run_battle
from croniter import croniter
from django.conf import settings
import json


class BattleViewSet(ModelViewSet):
    queryset = Battle.objects.select_related("pokemon_a","pokemon_b","scenario","winner").order_by("-created_at")
    filter_backends = [SearchFilter]
    search_fields = ["status"]

    def get_queryset(self):
        qs = super().get_queryset()

        status = (self.request.query_params.get("status") or "").strip().upper()
        if status:
            if status == Battle.Status.SCHEDULED:
                # “Programado” efectivo: tiene cron y NO está corriendo
                qs = qs.filter(scheduled_cron__isnull=False).exclude(status=Battle.Status.RUNNING)
            elif status in dict(Battle.Status.choices):
                qs = qs.filter(status=status)
            # si no coincide con choices, no filtramos

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return BattleListSerializer
        if self.action in ("create", "update", "partial_update"):
            return BattleWriteSerializer
        return BattleDetailSerializer

    # --------- Acciones personalizadas ----------
    @action(detail=True, methods=["post"], url_path="execute")
    def execute(self, request, pk=None):
        battle = self.get_object()
        if battle.status == Battle.Status.RUNNING:
            return Response({"detail": "Battle ya en ejecución"}, status=409)
        task = run_battle.delay(battle.id)
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="schedule")
    def schedule(self, request, pk=None):
        battle = self.get_object()
        expr = request.data.get("cron") or request.data.get("scheduled_cron")
        try:
            croniter(expr)  # valida CRON
        except Exception:
            return Response({"cron": ["Expresión CRON inválida"]},
                            status=status.HTTP_400_BAD_REQUEST)

        battle.scheduled_cron = expr
        battle.status = Battle.Status.SCHEDULED
        battle.save(update_fields=["scheduled_cron", "status"])

        # Si usas django-celery-beat, registra/actualiza el periodic task
        if getattr(settings, "USE_DJANGO_CELERY_BEAT", False):
            from django_celery_beat.models import CrontabSchedule, PeriodicTask
            minute, hour, dom, month, dow = expr.split()
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=minute, hour=hour, day_of_week=dow,
                day_of_month=dom, month_of_year=month,
                timezone=getattr(settings, "TIME_ZONE", "UTC"),
            )
            PeriodicTask.objects.update_or_create(
                name=f"battle-{battle.id}",
                defaults={
                    "crontab": schedule,
                    "task": "battles.tasks.run_battle",
                    "args": json.dumps([battle.id]),
                },
            )
        return Response(BattleDetailSerializer(battle).data, status=200)