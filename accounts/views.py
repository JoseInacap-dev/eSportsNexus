from django.urls import reverse_lazy
from django.views.generic import CreateView

from accounts.forms import UserRegistrationForm


class SignUpView(CreateView):
    form_class = UserRegistrationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("accounts:login")
