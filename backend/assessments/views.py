from common.viewsets import ScopedModelViewSet

from .models import ClassGroup
from .serializers import ClassGroupSerializer


class ClassGroupViewSet(ScopedModelViewSet):
    queryset = ClassGroup.objects.all()
    serializer_class = ClassGroupSerializer
    owner_extra_fields = ("created_by",)
