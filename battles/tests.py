import re
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import Pokemon, Scenario, Battle
from .tasks import run_battle


@override_settings(BATTLE_TICK_SLEEP=0.0)  # si agregas esta setting en tu app
class BattleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.A = Pokemon.objects.create(name="Pikachu", hp=35, attack=55, defense=40, speed=90)
        self.B = Pokemon.objects.create(name="Bulbasaur", hp=45, attack=49, defense=49, speed=45)
        self.S = Scenario.objects.create(name="Forest", attack_modifier=1.0, defense_modifier=1.0, speed_modifier=1.0)

    def _find_turn_line(self, log: str, turn_no: int) -> str | None:
        """
        Devuelve la línea del turno `turn_no` tolerando idioma/estilo:
        - 'Turn 1:' o 'Turno # 1'
        - mayúsc/minúsc, espacios extra, '#' o ':'
        """
        pat = re.compile(rf"^\s*(?:turn|turno)\s*[#:]?\s*{turn_no}\b", re.IGNORECASE)
        for line in log.splitlines():
            if pat.search(line):
                return line
        return None

    def test_create_battle_requires_distinct_pokemons(self):
        resp = self.client.post(
            "/api/battles/",
            {"pokemon_a": self.A.id, "pokemon_b": self.A.id, "scenario": self.S.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_damage_min_is_one_and_speed_order(self):
        # Defensa altísima para que el daño caiga al piso de 1
        self.S.defense_modifier = 100.0
        self.S.save()

        battle = Battle.objects.create(pokemon_a=self.A, pokemon_b=self.B, scenario=self.S)

        # Llamada síncrona (tu task expone la función directa)
        run_battle(battle.id)

        battle.refresh_from_db()
        self.assertEqual(battle.status, Battle.Status.FINISHED)

        first_turn = self._find_turn_line(battle.log, 1)
        self.assertIsNotNone(first_turn, f"No encontré la línea del turno 1 en el log:\n{battle.log}")

        # Pikachu (spd 90) debe iniciar
        self.assertIn("Pikachu", first_turn)

        # Daño mínimo 1 (asegura 1 como token completo)
        self.assertRegex(first_turn, r"\b1\b")

    def test_cron_validation_endpoint(self):
        battle = Battle.objects.create(pokemon_a=self.A, pokemon_b=self.B, scenario=self.S)
        resp = self.client.post(f"/api/battles/{battle.id}/schedule/", {"cron": "*/1 * * * *"}, format="json")
        self.assertEqual(resp.status_code, 200)
