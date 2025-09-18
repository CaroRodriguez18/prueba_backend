from datetime import datetime
from django.db import models
from django.utils import timezone

class Battle(models.Model):
    class Status(models.TextChoices):
        PENDING   = "PENDING",   "Pendiente"
        SCHEDULED = "SCHEDULED", "Programado"
        RUNNING   = "RUNNING",   "En ejecución"
        FINISHED  = "FINISHED",  "Finalizado"
        FAILED    = "FAILED",    "Fallido"


    # Nota: usamos strings para evitar import circular entre módulos
    name = models.CharField(max_length=100, unique=True, null=True, blank=True)
    pokemon_a = models.ForeignKey("Pokemon", on_delete=models.CASCADE, related_name="battles_as_a")
    pokemon_b = models.ForeignKey("Pokemon", on_delete=models.CASCADE, related_name="battles_as_b")
    scenario  = models.ForeignKey("Scenario", on_delete=models.PROTECT)

    scheduled_cron = models.CharField(max_length=64, blank=True, null=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    winner = models.ForeignKey("Pokemon", on_delete=models.SET_NULL, null=True, blank=True, related_name="wins")
    log    = models.TextField(blank=True, default="")
    state  = models.JSONField(default=dict, blank=True)  # hp_a / hp_b en vivo

    run_count_total = models.PositiveIntegerField(default=0) # Manual y por cron
    run_count_cron  = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Battle #{self.id} ({self.pokemon_a} vs {self.pokemon_b})"

    @property
    def next_run_at(self) -> datetime | None:
        """Próxima ejecución según scheduled_cron, o None si no aplica / inválido."""
        if not self.scheduled_cron:
            return None
        # Import perezoso para no tumbar el arranque si falta la lib
        try:
            from croniter import croniter
        except Exception:
            return None
        try:
            base = timezone.now()
            nxt = croniter(self.scheduled_cron, base).get_next(datetime)
            if timezone.is_naive(nxt):
                nxt = timezone.make_aware(nxt)
            return timezone.localtime(nxt)
        except Exception:
            return None

    class Meta:
        ordering = ("-created_at",)
