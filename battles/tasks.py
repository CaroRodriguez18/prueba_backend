# battles/tasks.py
import json, time
from celery import shared_task
from django.db import transaction
from django.conf import settings
from redis import Redis
from .models import Battle
from django.utils import timezone

def _redis():
    return Redis.from_url(getattr(settings, "REDIS_URL", "redis://redis:6379/0"))

def _channel(battle_id: int) -> str:
    return f"battle:{battle_id}:events"

def _emit(battle_id: int, payload: dict):
    _redis().publish(_channel(battle_id), json.dumps(payload, ensure_ascii=False))

# ------- Helpers de formateo de log (solo UX) -------
def _fmt_stats(side: str, name: str, atk: float, deff: float, spd: float) -> str:
    # ⚙️ A(Pikachu)  ⚔️ 66.0  🛡️ 40.0  ⚡ 90.0
    return (f"⚙️  Estadísticas {side}({name})  "
            f"⚔️ {atk:.1f}  🛡️ {deff:.1f}  ⚡ {spd:.1f}")

def _fmt_turn(n: int, attacker: str, defender: str, damage: int, hp_defender: int, name_w: int) -> str:
    # # 01 │ Pikachu → Bulbasaur   💥  17   ❤️  28
    num = f"{n:>2}"
    atk = f"{attacker:<{name_w}}"
    dfn = f"{defender:<{name_w}}"
    dmg = f"{damage:>3}"
    hp  = f"{hp_defender:>3}"
    return f"Turno #{num} │ {atk} → {dfn}   💥 {dmg}   ❤️ {hp}"

def _sep(width: int = 64) -> str:
    return "─" * width
# -----------------------------------------------------

@shared_task(name="battles.tasks.run_battle")
def run_battle(battle_id: int):
    # Carga y “lock” para evitar concurrentes
    with transaction.atomic():
        battle = (Battle.objects
                  .select_related("pokemon_a","pokemon_b","scenario")
                  .select_for_update()
                  .get(id=battle_id))
        if battle.status == Battle.Status.RUNNING:
            return f"Battle {battle_id} already RUNNING"

        # Init combate
        A, B, S = battle.pokemon_a, battle.pokemon_b, battle.scenario
        atkA = A.attack * S.attack_modifier
        defA = A.defense * S.defense_modifier
        spdA = A.speed * S.speed_modifier
        atkB = B.attack * S.attack_modifier
        defB = B.defense * S.defense_modifier
        spdB = B.speed * S.speed_modifier
        hpA, hpB = A.hp, B.hp

        battle.status = Battle.Status.RUNNING
        battle.log = ""
        battle.winner = None
        battle.state = {"hp_a": hpA, "hp_b": hpB}
        battle.save(update_fields=["status","log","winner","state"])

    # Ancho para columnas de nombres
    name_w = max(len(A.name or "A"), len(B.name or "B"), 3)

    # Primer snapshot con formato UX
    lines = [
        f"🗺️  Escenario: {S.name}",
        _fmt_stats("A", A.name, atkA, defA, spdA),
        _fmt_stats("B", B.name, atkB, defB, spdB),
        _sep(),
        "🚀  ¡Comienza el combate!",
    ]
    Battle.objects.filter(id=battle_id).update(
        log="\n".join(lines),
        state={"hp_a": hpA, "hp_b": hpB},
    )
    _emit(battle_id, {"type":"tick","status":"RUNNING","hp_a":hpA,"hp_b":hpB,"log_append":"🚀  ¡Comienza el combate!      daño     hp"})

    # Bucle de turnos (ritmo pequeño para “tiempo real”)
    attacker_is_A = True if spdA >= spdB else False  # empate comienza A
    turn = 1
    try:
        while hpA > 0 and hpB > 0 and turn < 10000:
            if attacker_is_A:
                damage = max(1, round(atkA - defB))
                hpB = max(0, hpB - damage)
                line = _fmt_turn(turn, A.name, B.name, damage, hpB, name_w)
            else:
                damage = max(1, round(atkB - defA))
                hpA = max(0, hpA - damage)
                line = _fmt_turn(turn, B.name, A.name, damage, hpA, name_w)

            # Actualiza DB y emite evento
            lines.append(line)
            Battle.objects.filter(id=battle_id).update(
                log="\n".join(lines),
                state={"hp_a": hpA, "hp_b": hpB},
            )
            _emit(battle_id, {"type":"tick","status":"RUNNING","hp_a":hpA,"hp_b":hpB,"log_append":line})

            if hpA == 0 or hpB == 0:
                break

            attacker_is_A = not attacker_is_A
            turn += 1
            time.sleep(0.4)  # “animación”

        winner = A if hpA > 0 else B
        lines.append(_sep())
        lines.append(f"🏆  Ganador: {winner.name}")

        # si el combate tiene cron, tras terminar vuelve a "SCHEDULED"
        new_status = Battle.Status.SCHEDULED if battle.scheduled_cron else Battle.Status.FINISHED

        Battle.objects.filter(id=battle_id).update(
            status=new_status,
            winner=winner,
            log="\n".join(lines),
            state={"hp_a": max(hpA, 0), "hp_b": max(hpB, 0)},
            updated_at=timezone.now(),
        )

        _emit(battle_id, {
            "type": "done",
            "status": "SCHEDULED" if new_status == Battle.Status.SCHEDULED else "FINISHED",
            "hp_a": max(hpA, 0),
            "hp_b": max(hpB, 0),
            "winner": winner.name,
            "log_append": f"🏆  Ganador: {winner.name}",
        })

        return f"Battle {battle_id} {new_status}"

    except Exception as exc:
        # si hay cron, queda “SCHEDULED” para reintentos futuros; si no, “FAILED”
        new_status = Battle.Status.SCHEDULED if Battle.objects.filter(
            id=battle_id, scheduled_cron__isnull=False
        ).exists() else Battle.Status.FAILED
        Battle.objects.filter(id=battle_id).update(
            status=new_status,
            log=f"ERROR: {exc}",
            updated_at=timezone.now(),
        )
        _emit(battle_id, {
            "type": "error",
            "status": "SCHEDULED" if new_status == Battle.Status.SCHEDULED else "FAILED",
            "error": str(exc),
        })
        raise
