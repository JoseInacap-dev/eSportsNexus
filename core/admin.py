"""Utilidades compartidas para el admin de Django."""

from django.db import models

from core.widgets import NexusDateInput, NexusDateTimeInput


class NexusDateAdminMixin:
    """Aplica los selectores de fecha dd/mm/yyyy de la plataforma en el admin.

    Sobrescribe los widgets por defecto de Django (``AdminDateWidget`` y
    ``AdminSplitDateTime``) por inputs de texto gestionados con flatpickr,
    manteniendo el valor enviado en formato ISO.
    """

    formfield_overrides = {
        models.DateField: {"widget": NexusDateInput},
        models.DateTimeField: {"widget": NexusDateTimeInput},
    }
