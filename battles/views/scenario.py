# battles/views/scenario.py
from rest_framework import viewsets
from rest_framework.filters import SearchFilter

from ..models import Scenario
from ..serializers import ScenarioSerializer
from ..pagination import DefaultPagination


class ScenarioViewSet(viewsets.ModelViewSet):
    queryset = Scenario.objects.all().order_by("id")
    serializer_class = ScenarioSerializer
    pagination_class = DefaultPagination
    filter_backends = [SearchFilter]
    search_fields = ["name"]
