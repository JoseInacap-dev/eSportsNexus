from django import forms

from core.permissions import MANAGEMENT_ROLES
from organizations.models import Team
from training.models import TrainingSession


class TrainingSessionForm(forms.ModelForm):
    class Meta:
        model = TrainingSession
        fields = [
            "team",
            "title",
            "scheduled_at",
            "duration_minutes",
            "location",
            "objectives",
            "plan",
            "status",
        ]
        widgets = {
            "objectives": forms.Textarea(attrs={"rows": 3}),
            "plan": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and not user.is_superuser:
            self.fields["team"].queryset = Team.objects.filter(
                organization__memberships__user=user,
                organization__memberships__is_active=True,
                organization__memberships__role__in=MANAGEMENT_ROLES,
            ).distinct().select_related("organization", "game")
        else:
            self.fields["team"].queryset = Team.objects.select_related(
                "organization", "game"
            )
        self.fields["scheduled_at"].widget = forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        )
        self.fields["scheduled_at"].input_formats = ["%Y-%m-%dT%H:%M"]