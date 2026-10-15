"""Widgets reutilizables de la plataforma."""

from django import forms


class TeamCheckboxGrid(forms.CheckboxSelectMultiple):
    """SelecciA3n mA�ltiple de equipos en una grilla de casillas.

    Cada casilla recibe un atributo ``data-game`` con el identificador del
    juego del equipo, lo que permite filtrar dinA�micamente por juego desde el
    navegador. El diccionario ``games`` (``{"<pk>": "<game_id>"}``) se inyecta
    desde el formulario una vez definido el ``queryset``.
    """

    template_name = "widgets/team_checkbox_grid.html"

    def __init__(self, *args, games=None, **kwargs):
        self.games = games or {}
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        if value is not None:
            game_id = self.games.get(str(value))
            if game_id is not None:
                option["attrs"]["data-game"] = str(game_id)
        return option


class TeamChoiceSelect(forms.Select):
    """Selector de equipo con metadatos para vista previa de logo/organización."""

    template_name = "widgets/team_select.html"

    def __init__(self, *args, teams_meta=None, **kwargs):
        self.teams_meta = teams_meta or {}
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        if value is not None:
            meta = self.teams_meta.get(str(value))
            if meta:
                if meta.get("logo"):
                    option["attrs"]["data-logo"] = meta["logo"]
                if meta.get("org"):
                    option["attrs"]["data-org"] = meta["org"]
                if meta.get("org_logo"):
                    option["attrs"]["data-org-logo"] = meta["org_logo"]
                if meta.get("team"):
                    option["attrs"]["data-team-name"] = meta["team"]
        return option


class NexusDateInput(forms.DateInput):
    """Fecha con visualización dd/mm/yyyy (valor enviado en ISO).

    No usa el control nativo ``type="date"`` porque su formato depende del
    idioma del navegador del usuario. La capa JavaScript (flatpickr) muestra
    ``dd/mm/yyyy`` mientras el ``<input>`` real conserva ``YYYY-MM-DD``.
    """

    def __init__(self, attrs=None, format="%Y-%m-%d"):
        default_attrs = {"data-datepicker": "date", "autocomplete": "off"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs, format=format)


class NexusDateTimeInput(forms.DateTimeInput):
    """Fecha y hora con visualización dd/mm/yyyy HH:MM (valor enviado en ISO)."""

    def __init__(self, attrs=None, format="%Y-%m-%d %H:%M"):
        default_attrs = {"data-datepicker": "datetime", "autocomplete": "off"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs, format=format)
