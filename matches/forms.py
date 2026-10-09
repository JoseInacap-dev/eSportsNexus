from django import forms

from core.permissions import MANAGEMENT_ROLES
from matches.models import Match
from organizations.models import Organization, Team


class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = [
            "game",
            "home_team",
            "away_team",
            "away_name",
            "kind",
            "status",
            "scheduled_at",
            "tournament_name",
            "best_of",
            "home_score",
            "away_score",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        def visible_organizations():
            if user is not None and user.is_superuser:
                return Organization.objects.all()
            return Organization.objects.filter(
                memberships__user=user, memberships__is_active=True
            ).distinct()

        def manageable_organizations():
            if user is not None and user.is_superuser:
                return Organization.objects.all()
            return Organization.objects.filter(
                memberships__user=user,
                memberships__is_active=True,
                memberships__role__in=MANAGEMENT_ROLES,
            ).distinct()

        visible_orgs = visible_organizations()
        self.fields["home_team"].queryset = Team.objects.filter(
            organization__in=manageable_organizations()
        ).select_related("organization", "game")
        self.fields["away_team"].queryset = Team.objects.filter(
            organization__in=visible_orgs
        ).select_related("organization", "game")

        self.fields["scheduled_at"].widget = forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        )
        self.fields["scheduled_at"].input_formats = ["%Y-%m-%dT%H:%M"]