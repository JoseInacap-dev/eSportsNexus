import django.core.validators
import django.db.models.deletion
from django.db import migrations, models
from django.utils.text import slugify

LEGACY_FORMAT = "round_robin"


def build_tournaments(apps, schema_editor):
    """Crea un Torneo por cada nombre de torneo y enlaza sus partidos."""
    Match = apps.get_model("matches", "Match")
    Tournament = apps.get_model("matches", "Tournament")

    used_slugs = set(Tournament.objects.values_list("slug", flat=True))
    groups = {}

    matches = Match.objects.exclude(tournament_name="").exclude(
        tournament_name__isnull=True
    )
    for match in matches:
        key = (match.game_id, match.tournament_name)
        group = groups.setdefault(
            key, {"name": match.tournament_name, "game_id": match.game_id, "teams": set()}
        )
        group["teams"].add(match.home_team_id)
        group["teams"].add(match.away_team_id)

    for (game_id, name), group in groups.items():
        base = slugify(name)[:150] or "torneo"
        slug = base
        suffix = 2
        while slug in used_slugs:
            slug = f"{base}-{suffix}"
            suffix += 1
        used_slugs.add(slug)

        tournament = Tournament.objects.create(
            name=name,
            slug=slug,
            game_id=game_id,
            format=LEGACY_FORMAT,
            participants_count=max(len(group["teams"]), 2),
        )
        Match.objects.filter(
            game_id=game_id, tournament_name=name
        ).update(tournament_id=tournament.pk)


def unbuild_tournaments(apps, schema_editor):
    """Restaura el texto libre y elimina los torneos creados."""
    Match = apps.get_model("matches", "Match")
    Tournament = apps.get_model("matches", "Tournament")

    for tournament in Tournament.objects.all():
        Match.objects.filter(tournament_id=tournament.pk).update(
            tournament_name=tournament.name
        )
    Tournament.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("matches", "0002_remove_away_name_require_away_team_status_live"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tournament",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150, verbose_name="nombre")),
                (
                    "slug",
                    models.SlugField(
                        blank=True, max_length=160, unique=True, verbose_name="slug"
                    ),
                ),
                (
                    "format",
                    models.CharField(
                        choices=[
                            ("swiss", "Suizo"),
                            ("single_elimination", "Eliminación simple (Playoffs)"),
                            ("double_elimination", "Eliminación doble"),
                            ("round_robin", "Round Robin (liga)"),
                            ("groups_playoffs", "Grupos + Playoffs"),
                        ],
                        default="swiss",
                        max_length=32,
                        verbose_name="formato",
                    ),
                ),
                (
                    "participants_count",
                    models.PositiveSmallIntegerField(
                        default=2,
                        help_text="Número de participantes del torneo.",
                        validators=[django.core.validators.MinValueValidator(2)],
                        verbose_name="participantes",
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        help_text="Imagen representativa del torneo.",
                        null=True,
                        upload_to="tournaments/images/",
                        verbose_name="imagen",
                    ),
                ),
                (
                    "image_url",
                    models.URLField(blank=True, verbose_name="imagen (URL)"),
                ),
                (
                    "start_date",
                    models.DateField(blank=True, null=True, verbose_name="fecha de inicio"),
                ),
                (
                    "end_date",
                    models.DateField(blank=True, null=True, verbose_name="fecha de fin"),
                ),
                ("description", models.TextField(blank=True, verbose_name="descripción")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="creado"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="actualizado"),
                ),
                (
                    "game",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tournaments",
                        to="organizations.game",
                        verbose_name="juego",
                    ),
                ),
            ],
            options={
                "verbose_name": "torneo",
                "verbose_name_plural": "torneos",
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="tournament",
            constraint=models.UniqueConstraint(
                fields=("game", "name"), name="unique_tournament_name_per_game"
            ),
        ),
        migrations.AddField(
            model_name="match",
            name="tournament",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="matches",
                to="matches.tournament",
                verbose_name="torneo",
            ),
        ),
        migrations.RunPython(build_tournaments, unbuild_tournaments),
        migrations.RemoveField(
            model_name="match",
            name="tournament_name",
        ),
    ]
