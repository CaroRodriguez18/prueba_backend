from rest_framework.viewsets import ModelViewSet
from rest_framework.filters import SearchFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from croniter import croniter
from django.conf import settings
import json

from ..models import Battle
from ..serializers import (
    BattleListSerializer,
    BattleDetailSerializer,
    BattleWriteSerializer,
)
from ..tasks import run_battle

# helper para crear/actualizar el PeriodicTask
def _upsert_periodic_task_for_battle(battle):
    from django_celery_beat.models import CrontabSchedule, PeriodicTask

    minute, hour, dom, month, dow = battle.scheduled_cron.split()
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
            "kwargs": json.dumps({"source": "cron"}), 
            "enabled": True,
        },
    )

class BattleViewSet(ModelViewSet):
    queryset = Battle.objects.select_related("pokemon_a","pokemon_b","scenario","winner").order_by("-created_at")
    filter_backends = [SearchFilter]
    search_fields = ["status"]

    def get_queryset(self):
        qs = super().get_queryset()
        status = (self.request.query_params.get("status") or "").strip().upper()
        if status:
            if status == Battle.Status.SCHEDULED:
                qs = qs.filter(scheduled_cron__isnull=False).exclude(status=Battle.Status.RUNNING)
            elif status in dict(Battle.Status.choices):
                qs = qs.filter(status=status)
        return qs

    def create(self, request, *args, **kwargs):
        write = BattleWriteSerializer(data=request.data)
        write.is_valid(raise_exception=True)
        battle = write.save()

        if battle.scheduled_cron:  # si vino cron
            battle.status = Battle.Status.SCHEDULED
            battle.save(update_fields=["status"])
            _upsert_periodic_task_for_battle(battle)

        else:
            battle.status = Battle.Status.PENDING
            battle.save(update_fields=["status"])

        return Response(BattleDetailSerializer(battle).data, status=status.HTTP_201_CREATED)

    def get_serializer_class(self):
        if self.action == "list":
            return BattleListSerializer
        if self.action in ("create", "update", "partial_update"):
            return BattleWriteSerializer
        return BattleDetailSerializer

    @action(detail=True, methods=["post"], url_path="execute")
    def execute(self, request, pk=None):
        battle = self.get_object()
        if battle.status == Battle.Status.RUNNING:
            return Response({"detail": "Battle ya en ejecución"}, status=409)
        task = run_battle.delay(battle.id, source="manual")
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="schedule")
    def schedule(self, request, pk=None):
        battle = self.get_object()
        if battle.status == Battle.Status.RUNNING:
            return Response({"detail": "Battle en ejecución; no se puede reprogramar ahora"}, status=409)

        expr = (request.data.get("cron") or request.data.get("scheduled_cron") or "").strip()

        if expr == "":
            battle.scheduled_cron = None
            if battle.status == Battle.Status.SCHEDULED:
                battle.status = Battle.Status.PENDING
            battle.save(update_fields=["scheduled_cron", "status"])
            if getattr(settings, "USE_DJANGO_CELERY_BEAT", False):
                from django_celery_beat.models import PeriodicTask
                PeriodicTask.objects.filter(name=f"battle-{battle.id}").delete()
            return Response(BattleDetailSerializer(battle).data, status=200)

        try:
            croniter(expr)
        except Exception:
            return Response({"cron": ["Expresión CRON inválida"]}, status=400)

        battle.scheduled_cron = expr
        battle.status = Battle.Status.SCHEDULED
        battle.save(update_fields=["scheduled_cron", "status"])

        if getattr(settings, "USE_DJANGO_CELERY_BEAT", False):
            _upsert_periodic_task_for_battle(battle)

        return Response(BattleDetailSerializer(battle).data, status=200)
