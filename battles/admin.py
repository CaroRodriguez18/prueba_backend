from django.contrib import admin
from .models import Pokemon, Scenario, Battle

@admin.register(Pokemon)
class PokemonAdmin(admin.ModelAdmin):
    list_display = ("id","name","hp","attack","defense","speed")
    search_fields = ("name",)

@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ("id","name","attack_modifier","defense_modifier","speed_modifier")
    search_fields = ("name",)

@admin.register(Battle)
class BattleAdmin(admin.ModelAdmin):
    list_display = ("id","pokemon_a","pokemon_b","scenario","status","winner","created_at")
    list_filter = ("status","scenario")
    search_fields = ("pokemon_a__name","pokemon_b__name")
