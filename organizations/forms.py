from django import forms
from django.utils.text import slugify

from core.permissions import MANAGEMENT_ROLES
from organizations.models import Organization, Team


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "name",
            "abbreviation",
            "country",
            "website",
            "logo",
            "logo_url",
            "description",
            "founded_date",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["founded_date"].widget = forms.DateInput(
            attrs={"type": "date"}, format="%Y-%m-%d"
        )
        self.fields["founded_date"].input_formats = ["%Y-%m-%d"]

    def save(self, commit=True):
        organization = super().save(commit=False)
        if not organization.pk and not organization.slug:
            organization.slug = self._unique_slug(organization.name)
        if commit:
            organization.save()
        return organization

    @staticmethod
    def _unique_slug(name):
        base = slugify(name) or "organizacion"
        slug = base
        suffix = 2
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = [
            "organization",
            "game",
            "name",
            "slug",
            "logo",
            "description",
            "status",
            "founded_date",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "logo": forms.FileInput(attrs={"accept": "image/*"}),
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
