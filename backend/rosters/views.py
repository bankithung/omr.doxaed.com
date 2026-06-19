from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.scope import can_edit_class, scope_filter, visibility_q
from common.viewsets import ScopedModelViewSet

from .models import Roster, Student
from .serializers import RosterSerializer, StudentSerializer

_EDIT_DENIED = "You have view-only access to this folder; editing is not permitted."


def _roster_edit_ok(request, roster):
    """A roster is editable if it has no governing class (class-less → only its own
    creator/admin/solo) or the requester can edit its governing class."""
    if roster.class_group_id is None:
        # Class-less roster: solo owner / active-org admin / the roster creator.
        from common.scope import get_active_org, is_active_admin

        if get_active_org(request) is None:
            return True
        if is_active_admin(request):
            return True
        return roster.created_by_id == request.user.id
    return can_edit_class(request, roster.class_group)


class RosterViewSet(ScopedModelViewSet):
    queryset = Roster.objects.all()
    serializer_class = RosterSerializer
    owner_extra_fields = ("created_by",)

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .filter(visibility_q(self.request, "class_group__", "created_by"))
            .distinct()
        )
        # Optional ?class_group=<id> → the rosters that belong to ONE class (the
        # class-detail page uses this), or ?class_group=none → standalone rosters.
        cg = self.request.query_params.get("class_group")
        if cg == "none":
            qs = qs.filter(class_group__isnull=True)
        elif cg and cg.isdigit():
            qs = qs.filter(class_group_id=int(cg))
        return qs

    def perform_create(self, serializer):
        # If a class_group is given, creating a roster under it needs EDIT rights.
        cg = serializer.validated_data.get("class_group")
        if cg is not None and not can_edit_class(self.request, cg):
            raise PermissionDenied(_EDIT_DENIED)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        if not _roster_edit_ok(self.request, serializer.instance):
            raise PermissionDenied(_EDIT_DENIED)
        # If reassigning to a new class_group, also require EDIT on the target.
        new_cg = serializer.validated_data.get("class_group", serializer.instance.class_group)
        if new_cg is not None and not can_edit_class(self.request, new_cg):
            raise PermissionDenied(_EDIT_DENIED)
        serializer.save()

    def perform_destroy(self, instance):
        if not _roster_edit_ok(self.request, instance):
            raise PermissionDenied(_EDIT_DENIED)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="add_count")
    def add_count(self, request, pk=None):
        roster = self.get_object()  # already scoped to request.user via ScopedModelViewSet
        if not _roster_edit_ok(request, roster):
            raise PermissionDenied(_EDIT_DENIED)
        count = request.data.get("count")
        try:
            count = int(count)
        except (TypeError, ValueError):
            return Response({"count": "Must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
        if count < 1:
            return Response({"count": "Must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)

        students = [
            Student(roster=roster, roll_number=str(i))
            for i in range(1, count + 1)
        ]
        Student.objects.bulk_create(students)
        return Response({"created": count}, status=status.HTTP_201_CREATED)


class StudentViewSet(viewsets.ModelViewSet):
    """Child-scoped: filtered through the roster's owner (user or org)."""

    permission_classes = [IsAuthenticated]
    serializer_class = StudentSerializer

    def get_queryset(self):
        qs = Student.objects.filter(
            scope_filter(self.request, "roster__")
            & visibility_q(self.request, "roster__class_group__", "roster__created_by")
        ).distinct()
        roster_id = self.request.query_params.get("roster")
        if roster_id:
            qs = qs.filter(roster_id=roster_id)
        return qs

    def perform_create(self, serializer):
        # Student.roster is scope-validated by the serializer; gate EDIT here.
        self._gate_edit(serializer.validated_data["roster"])
        serializer.save()

    def perform_update(self, serializer):
        # Gate BOTH source and destination roster: a writable `roster` FK would
        # otherwise let a member move a (PII-bearing) student into a roster they
        # can only VIEW or cannot see.
        self._gate_edit(serializer.instance.roster)
        new_roster = serializer.validated_data.get("roster", serializer.instance.roster)
        self._gate_edit(new_roster)
        serializer.save()

    def perform_destroy(self, instance):
        self._gate_edit(instance.roster)
        instance.delete()

    def _gate_edit(self, roster):
        if not _roster_edit_ok(self.request, roster):
            raise PermissionDenied(_EDIT_DENIED)
