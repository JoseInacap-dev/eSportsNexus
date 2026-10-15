"""Cálculo de grupos, tablas de posiciones y llaves de un torneo.

Solo visualización: no genera partidos. Las posiciones se derivan de los
partidos ya asociados al torneo (``Match.tournament``) que estén finalizados.
"""

import math

from django.utils.translation import gettext_lazy as _

from matches.models import Tournament


def _ordered_participants(tournament):
    """Participantes ordenados por posición (seed) y, si falta, por nombre."""
    participants = list(tournament.participants.select_related("team", "team__game"))
    return sorted(
        participants,
        key=lambda participant: (
            participant.seed is None,
            participant.seed or 0,
            participant.team.name.lower(),
        ),
    )


def _empty_stats(team):
    return {
        "team": team,
        "played": 0,
        "wins": 0,
        "losses": 0,
        "score_for": 0,
        "score_against": 0,
        "diff": 0,
        "points": 0,
    }


def _compute_standings(teams, matches):
    """Calcula la tabla de posiciones de un conjunto de equipos."""
    stats = {team.pk: _empty_stats(team) for team in teams}
    for match in matches:
        if not match.has_score or not match.is_finished:
            continue
        if match.home_team_id not in stats or match.away_team_id not in stats:
            continue
        home = stats[match.home_team_id]
        away = stats[match.away_team_id]
        home["played"] += 1
        away["played"] += 1
        home["score_for"] += match.home_score
        home["score_against"] += match.away_score
        away["score_for"] += match.away_score
        away["score_against"] += match.home_score
        if match.home_score > match.away_score:
            home["wins"] += 1
            away["losses"] += 1
        elif match.away_score > match.home_score:
            away["wins"] += 1
            home["losses"] += 1
    rows = list(stats.values())
    for row in rows:
        row["diff"] = row["score_for"] - row["score_against"]
        row["points"] = row["wins"] * 3
    rows.sort(
        key=lambda row: (
            -row["points"],
            -row["diff"],
            -row["score_for"],
            row["team"].name.lower(),
        )
    )
    return rows


def _finished_matches(tournament):
    return [
        match
        for match in tournament.matches.select_related("home_team", "away_team")
        if match.is_finished and match.has_score
    ]


def build_standings(tournament):
    """Tabla única para formatos de liga (round robin) o suizo."""
    teams = [participant.team for participant in _ordered_participants(tournament)]
    return {"name": None, "rows": _compute_standings(teams, _finished_matches(tournament))}


def _snake_assign(participants, labels):
    """Reparto equilibrado tipo serpiente de participantes en grupos."""
    groups_count = len(labels)
    assignment = {}
    for index, participant in enumerate(participants):
        row = index // groups_count
        position = index % groups_count
        if row % 2 == 1:
            position = groups_count - 1 - position
        assignment[participant.pk] = labels[position]
    return assignment


def build_groups(tournament):
    """Grupos con sus tablas de posiciones (formato Grupos + Playoffs)."""
    participants = _ordered_participants(tournament)
    if not participants:
        return []

    labels = [chr(ord("A") + index) for index in range(max(tournament.groups_count, 1))]
    auto_assignment = {}
    if any(not p.group_name for p in participants):
        auto_assignment = _snake_assign(participants, labels)

    buckets = {}
    for participant in participants:
        name = participant.group_name or auto_assignment.get(participant.pk, "")
        buckets.setdefault(name or "—", []).append(participant)

    matches = _finished_matches(tournament)
    groups = []
    for name in sorted(buckets):
        members = buckets[name]
        teams = [participant.team for participant in members]
        groups.append(
            {"name": name, "rows": _compute_standings(teams, matches), "count": len(teams)}
        )
    return groups


def playoff_qualifiers(groups, per_group=2):
    """Equipos clasificados (top ``per_group`` de cada grupo) para el cuadro."""
    qualified = []
    for group in groups:
        for row in group["rows"][:per_group]:
            qualified.append(row["team"])
    return qualified


def _bracket_order(size):
    """Orden estándar de siembra para una llave de ``size`` posiciones."""
    order = [1]
    while len(order) < size:
        n = len(order) * 2
        order = [value for seed in order for value in (seed, n + 1 - seed)]
    return order


def _round_name(matches_count):
    names = {
        1: _("Final"),
        2: _("Semifinales"),
        4: _("Cuartos de final"),
        8: _("Octavos de final"),
    }
    return names.get(matches_count, _("Ronda de %(n)d") % {"n": matches_count * 2})


def _match_defaults():
    """Claves de presentación comunes a todos los cruces de la llave.

    Mantenerlas siempre presentes evita condicionales frágiles en el template
    y permite decorar con datos reales solo cuando exista un ``Match``.
    """
    return {
        "has_score": False,
        "home_score": None,
        "away_score": None,
        "status": "",
        "status_display": "",
        "is_live": False,
        "is_finished": False,
        "match_pk": None,
        "scheduled_at": None,
        "best_of": None,
    }


def _tournament_match_index(tournament):
    """Índice de partidos del torneo por par de equipos (sin importar orden).

    La llave no guarda una posición (ronda/slot), así que el enlace con los
    partidos reales se hace por el enfrentamiento. Si un cruce se repite, se
    prefiere el partido finalizado y, en su defecto, el que esté en vivo.
    """
    index = {}
    for match in tournament.matches.select_related("home_team", "away_team"):
        key = frozenset((match.home_team_id, match.away_team_id))
        current = index.get(key)
        if current is None:
            index[key] = match
            continue
        current_rank = (current.is_finished, current.is_live)
        new_rank = (match.is_finished, match.is_live)
        if new_rank > current_rank:
            index[key] = match
    return index


def _decorate_match(match, match_index):
    """Añade marcador, estado y ganador real a un cruce de la llave."""
    home = match.get("home")
    away = match.get("away")
    if not home or not away or not match_index:
        return match

    real = match_index.get(frozenset((home.pk, away.pk)))
    if real is None:
        return match

    match["match_pk"] = real.pk
    match["status"] = real.status
    match["status_display"] = real.get_status_display()
    match["is_live"] = real.is_live
    match["is_finished"] = real.is_finished
    match["has_score"] = real.has_score
    match["home_score"] = real.home_score
    match["away_score"] = real.away_score
    match["scheduled_at"] = real.scheduled_at
    match["best_of"] = real.best_of
    if real.is_finished:
        match["winner"] = real.winner or match.get("winner")
    return match


def _decorate_rounds(rounds, match_index):
    for round_data in rounds:
        for match in round_data["matches"]:
            _decorate_match(match, match_index)


# Geometría del árbol de la llave (coordenadas en píxeles CSS).
_BRACKET_PAD = 8
_BRACKET_HEADER = 34
_BRACKET_NODE_W = 210
_BRACKET_NODE_H = 92
_BRACKET_COL_GAP = 72
_BRACKET_ROW_GAP = 16


def _px(value):
    """Formatea una coordenada para incrustarla en estilos/paths SVG."""
    return f"{value:.1f}"


def _layout_bracket(rounds):
    """Calcula la posición de cada cruce y las líneas conectoras del árbol.

    La ronda 0 reparte sus cruces a lo largo del eje vertical; cada ronda
    siguiente centra sus cruces entre los alimentadores de la ronda previa,
    de modo que el resultado es el árbol clásico de eliminación.
    """
    if not rounds or not rounds[0]["matches"]:
        return None

    node_w = _BRACKET_NODE_W
    node_h = _BRACKET_NODE_H
    col_gap = _BRACKET_COL_GAP
    pitch = node_h + _BRACKET_ROW_GAP
    top_base = _BRACKET_HEADER + _BRACKET_PAD

    col_x = [_BRACKET_PAD + index * (node_w + col_gap) for index in range(len(rounds))]

    centers = []
    first_centers = [top_base + node_h / 2.0 + index * pitch for index in range(len(rounds[0]["matches"]))]
    centers.append(first_centers)
    for r_index in range(1, len(rounds)):
        previous = centers[r_index - 1]
        current = []
        prev_count = len(previous)
        count = len(rounds[r_index]["matches"])
        for index in range(count):
            start = (index * prev_count) // count
            end = ((index + 1) * prev_count) // count - 1
            feeders = previous[start : end + 1] or [previous[min(start, prev_count - 1)]]
            center = sum(feeders) / len(feeders)
            current.append(center)
        centers.append(current)

    paths = []
    for r_index in range(1, len(rounds)):
        prev_count = len(rounds[r_index - 1]["matches"])
        count = len(rounds[r_index]["matches"])
        prev_x = col_x[r_index - 1]
        cur_x = col_x[r_index]
        prev_right = prev_x + node_w
        mid_x = prev_right + col_gap / 2.0
        for index in range(count):
            start = (index * prev_count) // count
            end = ((index + 1) * prev_count) // count - 1
            feeders = list(range(start, end + 1)) or [min(start, prev_count - 1)]
            stubs = " ".join(
                f"M {_px(prev_right)} {_px(centers[r_index - 1][f])} H {_px(mid_x)}"
                for f in feeders
            )
            paths.append(stubs)
            if len(feeders) > 1:
                ys = [centers[r_index - 1][f] for f in feeders]
                paths.append(f"M {_px(mid_x)} {_px(min(ys))} V {_px(max(ys))}")
            paths.append(
                f"M {_px(mid_x)} {_px(centers[r_index][index])} H {_px(cur_x)}"
            )

    for r_index, round_data in enumerate(rounds):
        for index, match in enumerate(round_data["matches"]):
            match["x"] = col_x[r_index]
            match["y"] = centers[r_index][index] - node_h / 2.0

    first_count = len(rounds[0]["matches"])
    height = top_base + (first_count - 1) * pitch + node_h + _BRACKET_PAD
    width = col_x[-1] + node_w + _BRACKET_PAD

    titles = [
        {
            "name": round_data["name"],
            "count": len(round_data["matches"]),
            "x": col_x[r_index],
        }
        for r_index, round_data in enumerate(rounds)
    ]

    return {
        "node_w": node_w,
        "node_h": node_h,
        "width": width,
        "height": height,
        "paths": paths,
        "titles": titles,
    }


def _build_single_bracket(teams):
    count = len(teams)
    if count < 2:
        return None

    size = 1
    while size < count:
        size *= 2
    byes = size - count
    seeds = list(teams)

    order = _bracket_order(size)
    first_round = []
    match_number = 0
    for position in range(0, size, 2):
        match_number += 1
        home_seed = order[position]
        away_seed = order[position + 1]
        home = seeds[home_seed - 1] if home_seed <= count else None
        away = seeds[away_seed - 1] if away_seed <= count else None
        bye = (home is None) != (away is None)
        entry = {
            "number": match_number,
            "home": home,
            "away": away,
            "home_seed": home_seed if home else None,
            "away_seed": away_seed if away else None,
            "home_label": str(home) if home else _("BYE"),
            "away_label": str(away) if away else _("BYE"),
            "bye": bye,
            "winner": home or away if bye else None,
        }
        entry.update(_match_defaults())
        first_round.append(entry)

    rounds = [{"name": _round_name(len(first_round)), "matches": first_round}]
    previous = first_round
    while len(previous) > 1:
        current = []
        for index in range(0, len(previous), 2):
            match_number += 1
            left = previous[index]
            right = previous[index + 1]
            left_team = left["winner"]
            right_team = right["winner"]
            entry = {
                "number": match_number,
                "home": left_team,
                "away": right_team,
                "home_seed": None,
                "away_seed": None,
                "home_label": str(left_team)
                if left_team
                else _("Ganador M%(n)d") % {"n": left["number"]},
                "away_label": str(right_team)
                if right_team
                else _("Ganador M%(n)d") % {"n": right["number"]},
                "bye": False,
                "winner": None,
            }
            entry.update(_match_defaults())
            current.append(entry)
        rounds.append({"name": _round_name(len(current)), "matches": current})
        previous = current

    return {"size": size, "byes": byes, "rounds": rounds}


def _build_lower_bracket(size):
    """Estructura simplificada de la llave inferior de doble eliminación."""
    upper_rounds = max(int(math.log2(size)), 1)
    lower_rounds = max(2 * upper_rounds - 2, 1)
    rounds = []
    for index in range(1, lower_rounds + 1):
        count = max(1, size // (2 ** ((index + 1) // 2 + 1)))
        matches = []
        for match_index in range(count):
            entry = {
                "number": index * 1000 + match_index,
                "home": None,
                "away": None,
                "home_seed": None,
                "away_seed": None,
                "home_label": _("Por definir"),
                "away_label": _("Por definir"),
                "bye": False,
                "winner": None,
            }
            entry.update(_match_defaults())
            matches.append(entry)
        rounds.append({"name": _("Ronda %(n)d") % {"n": index}, "matches": matches})
    return {"size": size, "byes": 0, "rounds": rounds}


def build_bracket(tournament, teams=None):
    """Llave(s) de un torneo de eliminación (simple o doble).

    ``teams`` permite construir la llave a partir de una lista concreta
    (p. ej. los clasificados de la fase de grupos). Si no se entrega, se usan
    todos los participantes ordenados por posición.
    """
    if teams is None:
        teams = [participant.team for participant in _ordered_participants(tournament)]

    upper = _build_single_bracket(teams)
    if upper is None:
        return None

    match_index = _tournament_match_index(tournament)
    _decorate_rounds(upper["rounds"], match_index)

    if tournament.format == Tournament.Format.DOUBLE_ELIMINATION:
        lower = _build_lower_bracket(upper["size"])
        _decorate_rounds(lower["rounds"], match_index)
        return {
            "size": upper["size"],
            "byes": upper["byes"],
            "participants": len(teams),
            "brackets": [
                {
                    "name": _("Llave superior"),
                    "rounds": upper["rounds"],
                    "layout": _layout_bracket(upper["rounds"]),
                },
                {
                    "name": _("Llave inferior"),
                    "rounds": lower["rounds"],
                    "layout": _layout_bracket(lower["rounds"]),
                },
            ],
        }

    return {
        "size": upper["size"],
        "byes": upper["byes"],
        "participants": len(teams),
        "brackets": [
            {
                "name": _("Llave"),
                "rounds": upper["rounds"],
                "layout": _layout_bracket(upper["rounds"]),
            }
        ],
    }
