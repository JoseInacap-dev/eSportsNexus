import django.db.models.deletion
from django.db import migrations, models


def remove_external_opponents(apps, schema_editor):
    """Elimina partidos con rival externo: ahora ambos equipos son registrados."""
    Match = apps.get_model("matches", "Match")
    Match.objects.filter(away_team__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("matches", "0001_initial"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            remove_external_opponents, migrations.RunPython.noop
        ),
        migrations.RemoveConstraint(
            model_name="match",
            name="match_requires_opponent",
        ),
        migrations.RemoveField(
            model_name="match",
            name="away_name",
        ),
        migrations.AlterField(
            model_name="match",
            name="away_team",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="away_matches",
                to="organizations.team",
                verbose_name="equipo visitante",
            ),
        ),
        migrations.AlterField(
            model_name="match",
            name="status",
            field=models.CharField(
                choices=[
                    ("scheduled", "Programado"),
                    ("live", "En vivo"),
                    ("finished", "Finalizado"),
                    ("cancelled", "Cancelado"),
                    ("postponed", "Aplazado"),
                ],
                default="scheduled",
                max_length=16,
                verbose_name="estado",
            ),
        ),
    ]
