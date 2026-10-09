from django import forms
from django.contrib.auth.forms import UserCreationForm

from accounts.models import User


class UserRegistrationForm(UserCreationForm):
    """Registro de usuarios de la plataforma."""

    email = forms.EmailField(required=True, label="Correo electrónico")

    class Meta:
        model = User
        fields = ("username", "email", "display_name")

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe un usuario con ese correo.")
        return email
