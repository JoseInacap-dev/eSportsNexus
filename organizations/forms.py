from django import forms

from core.permissions import MANAGEMENT_ROLES
from organizations.models import Organization, Team


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = [
            "organization",
            "game",
            "name",
            "slug",
            "description",
            "status",
            "founded_date",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and not user.is_superuser:
            self.fields["organization"].queryset = Organization.objects.filter(
                memberships__user=user,
                memberships__is_active=True,
                memberships__role__in=MANAGEMENT_ROLES,
            ).distinct()
        else:
            self.fields["organization"].queryset = Organization.objects.all()
        self.fields["founded_date"].widget = forms.DateInput(
            attrs={"type": "date"}, format="%Y-%m-%d"
        )
        self.fields["founded_date"].input_formats = ["%Y-%m-%d"]
