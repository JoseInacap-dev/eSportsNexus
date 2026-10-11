from django.urls import reverse_lazy
from django.views.generic import CreateView

from accounts.forms import UserRegistrationForm


class SignUpView(CreateView):
    form_class = UserRegistrationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        from accounts.models import OrganizationMembership
        from organizations.models import Organization

        default_org = Organization.objects.filter(is_active=True).first()
        if default_org and self.object:
            OrganizationMembership.objects.get_or_create(
                user=self.object,
                organization=default_org,
                defaults={
                    "role": OrganizationMembership.Role.OWNER,
                    "is_active": True,
                },
            )
        return response
