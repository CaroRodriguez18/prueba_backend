# battles/views/pokemon.py
from django.db.models import Max
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from ..models.pokemon import Pokemon
from ..serializers import PokemonSerializer
from ..pagination import DefaultPagination


class PokemonViewSet(viewsets.ModelViewSet):
    queryset = Pokemon.objects.all().order_by("id")
    serializer_class = PokemonSerializer
    pagination_class = DefaultPagination
    filter_backends = [SearchFilter]
    search_fields = ["name"]

    def list(self, request, *args, **kwargs):
        """
        Pagina el queryset filtrado y añade máximos globales (hp/atk/def/spd)
        para que el front pinte barras a escala del conjunto actual.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)

        agg = queryset.aggregate(
            max_hp=Max("hp"),
            max_attack=Max("attack"),
            max_defense=Max("defense"),
            max_speed=Max("speed"),
        )
        paginated = self.get_paginated_response(serializer.data).data
        paginated["max_stats"] = {
            "hp": agg["max_hp"] or 1,
            "attack": agg["max_attack"] or 1,
            "defense": agg["max_defense"] or 1,
            "speed": agg["max_speed"] or 1,
        }
        return Response(paginated)
