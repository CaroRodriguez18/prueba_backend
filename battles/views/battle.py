from rest_framework.viewsets import ModelViewSet
from rest_framework.filters import SearchFilter
from ..models import Battle
from ..serializers import (
    BattleListSerializer,
    BattleDetailSerializer,
    BattleWriteSerializer,
    ScheduleSerializer,
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
