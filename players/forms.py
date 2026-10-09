from django import forms

from players.models import Player


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = [
            "first_name",
            "last_name",
            "nickname",
            "email",
            "phone",
            "birth_date",
            "country",
            "user",
        ]
        widgets = {"birth_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["birth_date"].widget = forms.DateInput(
            attrs={"type": "date"}, format="%Y-%m-%d"
        )
        self.fields["birth_date"].input_formats = ["%Y-%m-%d"]
