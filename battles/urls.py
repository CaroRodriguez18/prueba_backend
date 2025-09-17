from rest_framework import routers
from .views import PokemonViewSet, ScenarioViewSet, BattleViewSet

router = routers.DefaultRouter()
router.register(r"pokemons", PokemonViewSet)
router.register(r"scenarios", ScenarioViewSet)
router.register(r"battles", BattleViewSet)

urlpatterns = router.urls