"""Descarga logos oficiales para las organizaciones que aún no tienen uno.

Las fuentes están verificadas manualmente (escudo oficial de cada club). El
comando solo actúa sobre organizaciones sin logo salvo que se use
``--overwrite``; nunca deja un logo "a medias": si la descarga o la conversión
fallan, la organización se queda como estaba.
"""

import io
import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db.models import Q
from PIL import Image

from organizations.models import Organization

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36"
)
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Referer": "https://en.wikipedia.org/",
}

# Fuente por abreviatura de organización (verificadas una a una).
SOURCES = {
    "BLG": "https://thumb.wikimedia.org/wikipedia/en/thumb/6/66/Bilibili_Gaming_logo_%282021%29.png/330px-Bilibili_Gaming_logo_%282021%29.png",
    "C9": "https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f7/Cloud9_logo_c._2023.svg/500px-Cloud9_logo_c._2023.svg.png",
    "DRX": "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/34/DRX_logo_2023.png/330px-DRX_logo_2023.png",
    "DK": "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/20/DPlus_KIA_Logo.svg/500px-DPlus_KIA_Logo.svg.png",
    "EDG": "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/33/Edward_Gaming_logo.png/330px-Edward_Gaming_logo.png",
    "FPX": "https://thumb.wikimedia.org/wikipedia/en/thumb/2/2d/FPX_Esports_logo.svg/500px-FPX_Esports_logo.svg.png",
    "HLE": "https://thumb.wikimedia.org/wikipedia/commons/thumb/9/99/Hanwha_Life_Esports_logo.svg/500px-Hanwha_Life_Esports_logo.svg.png",
    "MAD": "https://thumb.wikimedia.org/wikipedia/en/thumb/8/84/MAD_Lions_logo.svg/330px-MAD_Lions_logo.svg.png",
    "SK": "https://thumb.wikimedia.org/wikipedia/en/thumb/4/4d/SK_Gaming_logo.svg/500px-SK_Gaming_logo.svg.png",
    "TH": "https://thumb.wikimedia.org/wikipedia/en/thumb/6/62/Team_Heretics_logo.svg/500px-Team_Heretics_logo.svg.png",
    "VIT": "https://thumb.wikimedia.org/wikipedia/en/thumb/4/49/Team_Vitality_logo.svg/500px-Team_Vitality_logo.svg.png",
    "TES": "https://thumb.wikimedia.org/wikipedia/en/thumb/a/ac/Top_Esports_logo.png/330px-Top_Esports_logo.png",
    "WBG": "https://upload.wikimedia.org/wikipedia/en/7/75/Weibo_Gaming_logo.png",
    "NRG": "http://nrg.gg/cdn/shop/files/NRG_logo.jpg?v=1789524736",
    "KT": "https://image.static.bstage.in/cdn-cgi/image/metadata=none/rolster/86bafb88-7c23-4e57-be8a-f8f27bd05249/9c5aeb3c-2c7f-4396-8728-38e7a45fad39/ori.png",
    "LEV": "http://dcdn-us.mitiendanube.com/stores/004/038/274/themes/common/logo-1519495282-1716010302-609cd7894aa829074431b0fdcc70cc0c1716010302.png",
}

MAX_SIZE = 256
# El fondo se elige por contraste con el logo para que siempre sea visible
# sobre la tarjeta oscura del tema NEXUS.
DARK_BACKGROUND = (11, 13, 18)      # --nexus-bg-main
LIGHT_BACKGROUND = (233, 237, 245)
LUMINANCE_THRESHOLD = 0.5


def _download(url):
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _average_luminance(image):
    """Luminancia media (0-1) de los píxeles no transparentes."""
    opaque = [(r, g, b) for r, g, b, a in image.getdata() if a >= 32]
    if not opaque:
        return 1.0
    total = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in opaque)
    return total / len(opaque) / 255.0


def _render_tile(data):
    """Convierte la descarga en una miniatura PNG cuadrada y legible."""
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)

    dark_logo = _average_luminance(image) < LUMINANCE_THRESHOLD
    background = LIGHT_BACKGROUND if dark_logo else DARK_BACKGROUND

    side = max(image.size)
    tile = Image.new("RGBA", (side, side), background + (255,))
    tile.alpha_composite(image, ((side - image.width) // 2, (side - image.height) // 2))
    tile = tile.convert("RGB")
    tile.thumbnail((MAX_SIZE, MAX_SIZE), Image.LANCZOS)
    return tile


class Command(BaseCommand):
    help = "Descarga y asigna logos oficiales a organizaciones sin logo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Reemplaza también las organizaciones que ya tienen logo.",
        )
        parser.add_argument(
            "--only",
            nargs="*",
            default=None,
            metavar="ABREV",
            help="Limita el proceso a estas abreviaturas (p. ej. C9 NRG).",
        )

    def handle(self, *args, **options):
        queryset = Organization.objects.order_by("abbreviation")
        if options["only"]:
            wanted = {value.upper() for value in options["only"]}
            queryset = queryset.filter(abbreviation__in=wanted)
        if not options["overwrite"]:
            queryset = queryset.filter(Q(logo="") | Q(logo__isnull=True))

        processed = 0
        failed = 0
        for organization in queryset:
            url = SOURCES.get(organization.abbreviation.upper())
            if not url:
                self.stdout.write(
                    self.style.WARNING(
                        f"{organization.abbreviation}: sin fuente definida, se omite."
                    )
                )
                continue
            try:
                tile = _render_tile(_download(url))
                buffer = io.BytesIO()
                tile.save(buffer, format="PNG")
                filename = f"{organization.slug or organization.abbreviation}.png".lower()
                organization.logo.save(
                    filename, ContentFile(buffer.getvalue()), save=True
                )
                processed += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{organization.abbreviation}: {organization.name} -> "
                        f"{organization.logo.name}"
                    )
                )
            except Exception as exc:  # pragma: no cover - depende de la red
                failed += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"{organization.abbreviation}: fallo ({exc.__class__.__name__}: {exc})"
                    )
                )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Listo: {processed} logo(s) asignado(s), {failed} fallo(s)."
            )
        )
