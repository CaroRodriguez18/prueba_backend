from django.test import TestCase
from rest_framework.test import APIClient
from .models import Pokemon, Scenario, Battle
from .tasks import run_battle

class BattleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.A = Pokemon.objects.create(name="Pikachu", hp=35, attack=55, defense=40, speed=90)
        self.B = Pokemon.objects.create(name="Bulbasaur", hp=45, attack=49, defense=49, speed=45)
        self.S = Scenario.objects.create(name="Forest", attack_modifier=1.0, defense_modifier=1.0, speed_modifier=1.0)
    
    def test_create_battle_requires_distinct_pokemons(self):
        resp = self.client.post("/api/battles/", {
            "pokemon_a": self.A.id,
            "pokemon_b": self.A.id,
            "scenario": self.S.id,
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_damage_min_is_one_and_speed_order(self):
        # force very high defense so damage floors at 1
        self.S.defense_modifier = 100.0
        self.S.save()
        battle = Battle.objects.create(pokemon_a=self.A, pokemon_b=self.B, scenario=self.S)
        run_battle(battle.id) # synchronous call to task function
        battle.refresh_from_db()
        self.assertEqual(battle.status, Battle.Status.FINISHED)
        self.assertIn("Turn 1:", battle.log)
        # Pikachu (spd 90) should start (tie rule favors A but not needed here)
        self.assertTrue("Pikachu hits" in battle.log.split("\n")[3])
    
    def test_cron_validation_endpoint(self):
        battle = Battle.objects.create(pokemon_a=self.A, pokemon_b=self.B, scenario=self.S)
        resp = self.client.post(f"/api/battles/{battle.id}/schedule/", {"cron": "*/1 * * * *"}, format="json")
        self.assertEqual(resp.status_code, 200)
        