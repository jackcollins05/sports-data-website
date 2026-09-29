#!/usr/bin/env python3
"""Build reproducible, website-ready 2025 college football tables.

Inputs are immutable source files under raw_data/. Existing outputs are
preserved unless --overwrite-existing is passed. IDs remain strings in CSVs.
"""

from __future__ import annotations

import csv
import argparse
import gzip
import json
import random
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw_data"
SUPPORT = RAW / "supporting_2025"
OUT = ROOT / "data" / "football_2025"
TEAM_BRANDING = ROOT / "data" / "team_branding.json"
AP_RANKINGS_SOURCE = SUPPORT / "espn_ap_top25_2025.json"

INPUTS = {
    "pbp": RAW / "play_by_play_2025.csv",
    "player_box": SUPPORT / "player_box_2025.csv",
    "schedule": SUPPORT / "cfb_schedule_2025.csv",
    "team_box": SUPPORT / "team_box_2025.csv",
    "rosters": SUPPORT / "cfb_rosters_2025.csv.gz",
}

OUTPUT_NAMES = [
    "players_2025.csv",
    "player_game_stats_2025.csv",
    "player_season_stats_2025.csv",
    "games_2025.csv",
    "team_game_stats_2025.csv",
    "fbs_players_2025.csv",
    "fbs_player_game_stats_2025.csv",
    "fbs_player_season_stats_2025.csv",
    "fbs_games_2025.csv",
    "fbs_team_game_stats_2025.csv",
    "ap_top25_2025.csv",
    "ap_top25_trends_2025.csv",
    "player_data_quality_2025.json",
]

PLAYER_GAME_STATS = [
    "passing_completions", "passing_attempts", "passing_yards",
    "passing_yards_per_attempt", "passing_touchdowns", "passing_interceptions",
    "adj_qbr", "rushing_attempts", "rushing_yards", "rushing_yards_per_attempt",
    "rushing_touchdowns", "long_rushing", "receptions", "receiving_yards",
    "receiving_yards_per_reception", "receiving_touchdowns", "long_reception",
    "fumbles", "fumbles_lost", "fumbles_recovered", "defensive_total_tackles",
    "defensive_solo_tackles", "defensive_sacks", "defensive_tackles_for_loss",
    "passes_defended", "quarterback_hurries", "defensive_touchdowns",
    "defensive_interceptions", "interception_yards", "interception_touchdowns",
    "kick_returns", "kick_return_yards", "kick_return_yards_per_return",
    "long_kick_return", "kick_return_touchdowns", "punt_returns",
    "punt_return_yards", "punt_return_yards_per_return", "long_punt_return",
    "punt_return_touchdowns", "field_goals_made", "field_goal_attempts",
    "field_goal_pct", "long_field_goal_made", "extra_points_made",
    "extra_point_attempts", "total_kicking_points", "punts", "punt_yards",
    "gross_avg_punt_yards", "punt_touchbacks", "punts_inside_20", "long_punt",
]

SUM_FIELDS = [
    "passing_completions", "passing_attempts", "passing_yards",
    "passing_touchdowns", "passing_interceptions", "rushing_attempts",
    "rushing_yards", "rushing_touchdowns", "receptions", "receiving_yards",
    "receiving_touchdowns", "fumbles", "fumbles_lost", "fumbles_recovered",
    "defensive_total_tackles", "defensive_solo_tackles", "defensive_sacks",
    "defensive_tackles_for_loss", "passes_defended", "quarterback_hurries",
    "defensive_touchdowns", "defensive_interceptions", "interception_yards",
    "interception_touchdowns", "kick_returns", "kick_return_yards",
    "kick_return_touchdowns", "punt_returns", "punt_return_yards",
    "punt_return_touchdowns", "field_goals_made", "field_goal_attempts",
    "extra_points_made", "extra_point_attempts", "total_kicking_points", "punts",
    "punt_yards", "punt_touchbacks", "punts_inside_20",
]

RATE_SOURCE_FIELDS = [
    "passing_yards_per_attempt", "rushing_yards_per_attempt",
    "receiving_yards_per_reception", "kick_return_yards_per_return",
    "punt_return_yards_per_return", "field_goal_pct", "gross_avg_punt_yards",
]

PLAYER_BOX_CATEGORY_COLUMNS: dict[str, dict[str, str]] = {
    "passing": {
        "passing_yards": "passingYards",
        "passing_yards_per_attempt": "yardsPerPassAttempt",
        "passing_touchdowns": "passingTouchdowns",
        "passing_interceptions": "interceptions",
        "adj_qbr": "adjQBR",
    },
    "rushing": {
        "rushing_attempts": "rushingAttempts",
        "rushing_yards": "rushingYards",
        "rushing_yards_per_attempt": "yardsPerRushAttempt",
        "rushing_touchdowns": "rushingTouchdowns",
        "long_rushing": "longRushing",
    },
    "receiving": {
        "receptions": "receptions",
        "receiving_yards": "receivingYards",
        "receiving_yards_per_reception": "yardsPerReception",
        "receiving_touchdowns": "receivingTouchdowns",
        "long_reception": "longReception",
    },
    "fumbles": {
        "fumbles": "fumbles", "fumbles_lost": "fumblesLost",
        "fumbles_recovered": "fumblesRecovered",
    },
    "defensive": {
        "defensive_total_tackles": "totalTackles",
        "defensive_solo_tackles": "soloTackles",
        "defensive_sacks": "sacks",
        "defensive_tackles_for_loss": "tacklesForLoss",
        "passes_defended": "passesDefended",
        "quarterback_hurries": "hurries",
        "defensive_touchdowns": "defensiveTouchdowns",
    },
    "interceptions": {
        "defensive_interceptions": "interceptions",
        "interception_yards": "interceptionYards",
        "interception_touchdowns": "interceptionTouchdowns",
    },
    "kickReturns": {
        "kick_returns": "kickReturns", "kick_return_yards": "kickReturnYards",
        "kick_return_yards_per_return": "yardsPerKickReturn",
        "long_kick_return": "longKickReturn",
        "kick_return_touchdowns": "kickReturnTouchdowns",
    },
    "puntReturns": {
        "punt_returns": "puntReturns", "punt_return_yards": "puntReturnYards",
        "punt_return_yards_per_return": "yardsPerPuntReturn",
        "long_punt_return": "longPuntReturn",
        "punt_return_touchdowns": "puntReturnTouchdowns",
    },
    "kicking": {
        "field_goal_pct": "fieldGoalPct",
        "long_field_goal_made": "longFieldGoalMade",
        "total_kicking_points": "totalKickingPoints",
    },
    "punting": {
        "punts": "punts", "punt_yards": "puntYards",
        "gross_avg_punt_yards": "grossAvgPuntYards",
        "punt_touchbacks": "touchbacks", "punts_inside_20": "puntsInside20",
        "long_punt": "longPunt",
    },
}


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required input is missing: {path.relative_to(ROOT)}")
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def decimal_value(value: Any) -> Decimal | None:
    raw = text(value).replace(",", "")
    if not raw or raw.lower() in {"na", "nan", "null", "none", "--"}:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def number_string(value: Decimal | int | None) -> str:
    if value is None:
        return ""
    d = value if isinstance(value, Decimal) else Decimal(value)
    if not d.is_finite():
        return ""
    normalized = d.normalize()
    out = format(normalized, "f")
    return "0" if out in {"-0", ""} else out


def pair_values(value: Any, separator: str) -> tuple[Decimal | None, Decimal | None]:
    raw = text(value)
    parts = raw.split(separator)
    if len(parts) != 2:
        return None, None
    return decimal_value(parts[0]), decimal_value(parts[1])


def ratio(numerator: Decimal | None, denominator: Decimal | None, percent: bool = False) -> Decimal | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    value = numerator / denominator
    return value * Decimal(100) if percent else value


def bool_string(value: Any) -> str:
    return "true" if text(value).lower() in {"true", "1", "yes"} else "false"


def write_csv(
    path: Path, columns: list[str], rows: list[dict[str, Any]], *, overwrite: bool = False,
) -> None:
    with path.open("w" if overwrite else "x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: text(row.get(col)) for col in columns})


def duplicate_count(rows: Iterable[dict[str, Any]], key_columns: tuple[str, ...]) -> int:
    seen: set[tuple[str, ...]] = set()
    duplicates = 0
    for row in rows:
        key = tuple(text(row.get(col)) for col in key_columns)
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return duplicates


def assert_nonnegative(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for field in fields:
        negatives = sum((decimal_value(row.get(field)) or Decimal(0)) < 0 for row in rows)
        result[field] = negatives
    return result


def normalize_player_category(
    category: str, source: dict[str, str], target: dict[str, Any],
) -> None:
    for output, input_name in PLAYER_BOX_CATEGORY_COLUMNS.get(category, {}).items():
        target[output] = number_string(decimal_value(source.get(input_name)))

    if category == "passing":
        comp, att = pair_values(source.get("completions/passingAttempts"), "/")
        target["passing_completions"] = number_string(comp)
        target["passing_attempts"] = number_string(att)
        target["passing_normalization_status"] = "normalized_fields"
        generic = [text(source.get(f"stat_{i}")) for i in range(1, 6)]
        if not any(text(source.get(c)) for c in (
            "completions/passingAttempts", "passingYards", "yardsPerPassAttempt",
            "passingTouchdowns", "interceptions", "adjQBR",
        )):
            # These unlabeled generic values are retained for audit; their meaning
            # cannot be established from this file because they never overlap the
            # normalized fields on passing rows.
            target["passing_normalization_status"] = "generic_fields_unmapped"
            for i, value in enumerate(generic, 1):
                target[f"unmapped_pass_stat_{i}"] = value

    elif category == "kicking":
        made, attempts = pair_values(source.get("fieldGoalsMade/fieldGoalAttempts"), "/")
        xp_made, xp_attempts = pair_values(source.get("extraPointsMade/extraPointAttempts"), "/")
        target["field_goals_made"] = number_string(made)
        target["field_goal_attempts"] = number_string(attempts)
        target["extra_points_made"] = number_string(xp_made)
        target["extra_point_attempts"] = number_string(xp_attempts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite-existing", action="store_true",
        help="replace generated files in data/football_2025 (never raw/source files)",
    )
    args = parser.parse_args()
    overwrite = args.overwrite_existing

    # Fail before reading or writing if outputs already exist unless explicitly
    # asked to regenerate website-ready files. Raw/source files are never written.
    existing = [OUT / name for name in OUTPUT_NAMES if (OUT / name).exists()]
    if existing and not overwrite:
        listing = "\n".join(str(p.relative_to(ROOT)) for p in existing)
        raise FileExistsError(
            f"Refusing to overwrite generated output file(s); pass --overwrite-existing to regenerate:\n{listing}"
        )
    for required in [TEAM_BRANDING, AP_RANKINGS_SOURCE]:
        if not required.is_file():
            raise FileNotFoundError(f"Required source is missing: {required.relative_to(ROOT)}")

    roster_rows = read_csv(INPUTS["rosters"])
    player_box_rows = read_csv(INPUTS["player_box"])
    schedule_rows = read_csv(INPUTS["schedule"])
    team_box_rows = read_csv(INPUTS["team_box"])

    with TEAM_BRANDING.open(encoding="utf-8") as handle:
        branding_document = json.load(handle)
    branding = branding_document.get("teams", {})
    team_brand_by_id = {
        text(values.get("id")): {**values, "team_name": name}
        for name, values in branding.items() if text(values.get("id"))
    }
    if len(team_brand_by_id) != len(branding):
        raise ValueError("Team branding has missing or duplicate team IDs")
    invalid_brand_divisions = {
        team_id: text(values.get("division")).lower()
        for team_id, values in team_brand_by_id.items()
        if text(values.get("division")).lower() not in {"fbs", "fcs"}
    }
    if invalid_brand_divisions:
        raise ValueError(f"Team branding has missing/unsupported divisions: {invalid_brand_divisions}")
    division_by_team_id = {
        team_id: text(values["division"]).upper()
        for team_id, values in team_brand_by_id.items()
    }

    schedule_team_ids = {row["home_id"] for row in schedule_rows} | {row["away_id"] for row in schedule_rows}
    missing_brand_teams = sorted(schedule_team_ids - set(team_brand_by_id))
    if missing_brand_teams:
        raise ValueError(f"Scheduled team IDs missing from team_branding.json: {missing_brand_teams}")
    roster_division_mismatches = [
        {"team_id": row["team_id"], "roster_division": text(row.get("division")),
         "branding_division": division_by_team_id.get(row["team_id"], "")}
        for row in roster_rows
        if text(row.get("division")).lower() != division_by_team_id.get(row["team_id"], "").lower()
    ]
    if roster_division_mismatches:
        raise ValueError(f"Roster/branding division disagreement on {len(roster_division_mismatches)} rows")

    # Preserve all identifier values as source strings.
    roster_key = ("season", "team_id", "athlete_id")
    roster_duplicates = duplicate_count(roster_rows, roster_key)
    if roster_duplicates:
        raise ValueError(f"Duplicate roster keys found: {roster_duplicates}")
    roster_map = {tuple(row[k] for k in roster_key): row for row in roster_rows}

    schedule_duplicates = duplicate_count(schedule_rows, ("game_id",))
    if schedule_duplicates:
        raise ValueError(f"Duplicate schedule game IDs found: {schedule_duplicates}")
    schedule_map = {row["game_id"]: row for row in schedule_rows}

    player_box_key = ("game_id", "team_id", "athlete_id", "category")
    player_box_duplicates = duplicate_count(player_box_rows, player_box_key)
    if player_box_duplicates:
        raise ValueError(f"Duplicate player-box keys found: {player_box_duplicates}")
    team_box_duplicates = duplicate_count(team_box_rows, ("game_id", "team_id"))
    if team_box_duplicates:
        raise ValueError(f"Duplicate team-box game/team keys found: {team_box_duplicates}")

    # Schedule authority: one canonical game row, including final points/winner.
    games: list[dict[str, Any]] = []
    game_columns = [
        "game_id", "season", "week", "season_type", "game_date", "home_team_id",
        "home_team", "home_abbreviation", "home_division", "home_score", "away_team_id", "away_team",
        "away_abbreviation", "away_division", "away_score", "winner_team_id", "winner", "venue",
        "attendance", "status", "neutral_site", "conference_competition",
    ]
    for src in schedule_rows:
        home_score = decimal_value(src.get("home_score"))
        away_score = decimal_value(src.get("away_score"))
        if home_score is not None and away_score is not None and home_score > away_score:
            winner_id, winner = src["home_id"], src["home_team"]
        elif home_score is not None and away_score is not None and away_score > home_score:
            winner_id, winner = src["away_id"], src["away_team"]
        else:
            winner_id, winner = "", ""
        games.append({
            "game_id": src["game_id"], "season": src["season"], "week": src["week"],
            "season_type": src["season_type"], "game_date": src["game_date"],
            "home_team_id": src["home_id"], "home_team": src["home_team"],
            "home_abbreviation": src["home_abbreviation"],
            "home_division": division_by_team_id[src["home_id"]], "home_score": src["home_score"],
            "away_team_id": src["away_id"], "away_team": src["away_team"],
            "away_abbreviation": src["away_abbreviation"],
            "away_division": division_by_team_id[src["away_id"]], "away_score": src["away_score"],
            "winner_team_id": winner_id, "winner": winner, "venue": src.get("venue", ""),
            "attendance": src.get("attendance", ""), "status": src.get("status", ""),
            "neutral_site": bool_string(src.get("neutral_site")),
            "conference_competition": bool_string(src.get("conference_competition")),
        })

    # One roster entry per player/team; unknown position is explicit, never inferred.
    player_columns = [
        "season", "athlete_id", "display_name", "full_name", "team_id", "team_name",
        "team_abbreviation", "division", "position", "position_abbreviation", "position_id", "jersey",
        "headshot_url", "team_logo_url", "team_logo_dark_url", "team_color",
        "team_alternate_color", "position_known",
    ]
    players: list[dict[str, Any]] = []
    unknown_roster_entries: list[dict[str, str]] = []
    for src in roster_rows:
        position_abbr = text(src.get("position_abbreviation"))
        known = position_abbr not in {"", "-"} and text(src.get("position", "")).lower() != "unknown"
        row = {
            "season": src["season"], "athlete_id": src["athlete_id"],
            "display_name": src.get("display_name") or src.get("athlete_display_name") or src.get("full_name", ""),
            "full_name": src.get("full_name") or src.get("athlete_display_name", ""),
            "team_id": src["team_id"], "team_name": src.get("team_display_name") or src.get("team_location", ""),
            "team_abbreviation": src.get("team_abbreviation", ""),
            "division": division_by_team_id[src["team_id"]],
            "position": src.get("position", ""), "position_abbreviation": position_abbr,
            "position_id": src.get("position_id", ""), "jersey": src.get("jersey", ""),
            "headshot_url": src.get("headshot_href", ""),
            "team_logo_url": src.get("logo_href", ""),
            "team_logo_dark_url": src.get("logo_dark_href", ""),
            "team_color": src.get("team_color", ""),
            "team_alternate_color": src.get("team_alternate_color", ""),
            "position_known": str(known).lower(),
        }
        players.append(row)
        if not known:
            unknown_roster_entries.append({"season": src["season"], "team_id": src["team_id"], "athlete_id": src["athlete_id"]})

    team_by_game: dict[str, dict[str, dict[str, str]]] = {}
    for game in schedule_rows:
        team_by_game[game["game_id"]] = {
            game["home_id"]: {"team": game["home_team"], "abbr": game["home_abbreviation"], "division": division_by_team_id[game["home_id"]], "opponent_id": game["away_id"], "opponent": game["away_team"], "opponent_division": division_by_team_id[game["away_id"]], "side": "home"},
            game["away_id"]: {"team": game["away_team"], "abbr": game["away_abbreviation"], "division": division_by_team_id[game["away_id"]], "opponent_id": game["home_id"], "opponent": game["home_team"], "opponent_division": division_by_team_id[game["home_id"]], "side": "away"},
        }

    # Pivot category-grain player rows into one player/game/team record.
    player_game_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    unknown_category_counts: Counter[str] = Counter()
    player_box_unmatched: list[dict[str, str]] = []
    passing_unmapped: list[dict[str, str]] = []
    roster_match_rows = 0
    player_box_unique_entities: set[tuple[str, str, str]] = set()
    matched_player_box_entities: set[tuple[str, str, str]] = set()
    player_box_ids_without_roster: set[str] = set()
    name_mismatch_entities: set[tuple[str, str, str]] = set()

    for src in player_box_rows:
        game_id, team_id, athlete_id = src["game_id"], src["team_id"], src["athlete_id"]
        schedule = schedule_map.get(game_id)
        if schedule is None:
            raise ValueError(f"Player-box game is absent from schedule: {game_id}")
        side_info = team_by_game[game_id].get(team_id)
        if side_info is None:
            raise ValueError(f"Player-box team is not a scheduled participant: {game_id}/{team_id}")
        entity = (src["season"], team_id, athlete_id)
        player_box_unique_entities.add(entity)
        roster = roster_map.get(entity)
        if roster is not None:
            roster_match_rows += 1
            matched_player_box_entities.add(entity)
            if text(src.get("athlete_name")).casefold() != text(roster.get("full_name")).casefold():
                name_mismatch_entities.add(entity)
        else:
            player_box_ids_without_roster.add(athlete_id)
            player_box_unmatched.append({
                "game_id": game_id, "season": src["season"], "team_id": team_id,
                "athlete_id": athlete_id, "category": src["category"],
            })

        key = (game_id, team_id, athlete_id)
        if key not in player_game_map:
            player_game_map[key] = {
                "game_id": game_id, "week": schedule["week"], "season": src["season"],
                "season_type": schedule["season_type"], "game_date": schedule["game_date"],
                "athlete_id": athlete_id,
                "player_name": src.get("athlete_name", ""),
                "display_name": (roster or {}).get("display_name") or src.get("athlete_name", ""),
                "full_name": (roster or {}).get("full_name") or src.get("athlete_name", ""),
                "team_id": team_id, "team": side_info["team"], "team_abbreviation": side_info["abbr"],
                "division": side_info["division"],
                "opponent_team_id": side_info["opponent_id"], "opponent": side_info["opponent"],
                "opponent_division": side_info["opponent_division"],
                "home_away": side_info["side"],
                "position": (roster or {}).get("position", ""),
                "position_abbreviation": (roster or {}).get("position_abbreviation", ""),
                "jersey": (roster or {}).get("jersey", src.get("jersey", "")),
                "roster_match": str(roster is not None).lower(),
                "position_known": str(bool(roster and text(roster.get("position_abbreviation")) not in {"", "-"})).lower(),
                **{field: "" for field in PLAYER_GAME_STATS},
                "passing_normalization_status": "no_passing_category",
                **{f"unmapped_pass_stat_{i}": "" for i in range(1, 6)},
            }
        target = player_game_map[key]
        category = src["category"]
        if category not in PLAYER_BOX_CATEGORY_COLUMNS:
            unknown_category_counts[category] += 1
        normalize_player_category(category, src, target)
        if category == "passing" and target["passing_normalization_status"] == "generic_fields_unmapped":
            passing_unmapped.append({
                "game_id": game_id, "week": schedule["week"], "team_id": team_id,
                "athlete_id": athlete_id, "player_name": src.get("athlete_name", ""),
                **{f"stat_{i}": text(src.get(f"stat_{i}")) for i in range(1, 6)},
            })

    if unknown_category_counts:
        raise ValueError(f"Unrecognized player-box categories: {dict(unknown_category_counts)}")

    player_games = list(player_game_map.values())
    player_game_columns = [
        "game_id", "week", "season", "season_type", "game_date", "athlete_id",
        "player_name", "display_name", "full_name", "team_id", "team", "team_abbreviation",
        "division", "opponent_team_id", "opponent", "opponent_division", "home_away",
        "position", "position_abbreviation",
        "jersey", "roster_match", "position_known", *PLAYER_GAME_STATS,
        "passing_normalization_status", *(f"unmapped_pass_stat_{i}" for i in range(1, 6)),
    ]

    # Season totals are sums of player-game count/yards fields. Rate statistics
    # are recalculated from season totals and attempts, never summed from games.
    totals_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for game_row in player_games:
        key = (game_row["season"], game_row["team_id"], game_row["athlete_id"])
        if key not in totals_map:
            totals_map[key] = {
                "season": game_row["season"], "athlete_id": game_row["athlete_id"],
                "player_name": game_row["player_name"], "display_name": game_row["display_name"],
                "full_name": game_row["full_name"], "team_id": game_row["team_id"],
                "team": game_row["team"], "team_abbreviation": game_row["team_abbreviation"],
                "division": game_row["division"],
                "position": game_row["position"], "position_abbreviation": game_row["position_abbreviation"],
                "jersey": game_row["jersey"], "roster_match": game_row["roster_match"],
                "position_known": game_row["position_known"], "games_played": 0,
                "passing_unmapped_games": 0,
                **{field: Decimal(0) for field in SUM_FIELDS},
                **{field: None for field in RATE_SOURCE_FIELDS},
                "adj_qbr_sum": Decimal(0), "adj_qbr_games": 0,
            }
        total = totals_map[key]
        total["games_played"] += 1
        if game_row["passing_normalization_status"] == "generic_fields_unmapped":
            total["passing_unmapped_games"] += 1
        for field in SUM_FIELDS:
            value = decimal_value(game_row.get(field))
            if value is not None:
                total[field] += value
        qbr = decimal_value(game_row.get("adj_qbr"))
        if qbr is not None:
            total["adj_qbr_sum"] += qbr
            total["adj_qbr_games"] += 1

    season_rate_fields = [
        "passing_completion_pct", "passing_yards_per_attempt", "rushing_yards_per_attempt",
        "receiving_yards_per_reception", "kick_return_yards_per_return",
        "punt_return_yards_per_return", "field_goal_pct", "extra_point_pct",
        "gross_avg_punt_yards", "average_adj_qbr",
    ]
    season_sum_fields = [*SUM_FIELDS, "games_played", "passing_unmapped_games"]
    player_seasons: list[dict[str, Any]] = []
    for total in totals_map.values():
        row = {k: (number_string(v) if isinstance(v, Decimal) else v) for k, v in total.items() if k not in {"adj_qbr_sum", "adj_qbr_games"}}
        row["passing_completion_pct"] = number_string(ratio(total["passing_completions"], total["passing_attempts"], percent=True))
        row["passing_yards_per_attempt"] = number_string(ratio(total["passing_yards"], total["passing_attempts"]))
        row["rushing_yards_per_attempt"] = number_string(ratio(total["rushing_yards"], total["rushing_attempts"]))
        row["receiving_yards_per_reception"] = number_string(ratio(total["receiving_yards"], total["receptions"]))
        row["kick_return_yards_per_return"] = number_string(ratio(total["kick_return_yards"], total["kick_returns"]))
        row["punt_return_yards_per_return"] = number_string(ratio(total["punt_return_yards"], total["punt_returns"]))
        row["field_goal_pct"] = number_string(ratio(total["field_goals_made"], total["field_goal_attempts"], percent=True))
        row["extra_point_pct"] = number_string(ratio(total["extra_points_made"], total["extra_point_attempts"], percent=True))
        row["gross_avg_punt_yards"] = number_string(ratio(total["punt_yards"], total["punts"]))
        row["average_adj_qbr"] = number_string(ratio(total["adj_qbr_sum"], Decimal(total["adj_qbr_games"])))
        player_seasons.append(row)
    season_columns = [
        "season", "athlete_id", "player_name", "display_name", "full_name", "team_id", "team",
        "team_abbreviation", "division", "position", "position_abbreviation", "jersey", "roster_match",
        "position_known", *season_sum_fields, *season_rate_fields,
    ]

    # Team box is the authority for team totals. Scores and dates come from schedule.
    team_game_map: dict[tuple[str, str], dict[str, Any]] = {}
    team_game_columns = [
        "game_id", "season", "week", "season_type", "game_date", "team_id", "team",
        "team_abbreviation", "division", "opponent_team_id", "opponent", "opponent_division",
        "home_away", "points_scored",
        "points_allowed", "first_downs", "total_yards", "net_passing_yards", "completions",
        "passing_attempts", "yards_per_pass", "rushing_yards", "rushing_attempts",
        "yards_per_rush_attempt", "third_down_conversions", "third_down_attempts",
        "third_down_pct", "fourth_down_conversions", "fourth_down_attempts", "fourth_down_pct",
        "penalties", "penalty_yards", "turnovers", "fumbles_lost", "interceptions_thrown",
        "possession_time", "possession_seconds",
    ]
    for src in team_box_rows:
        game_id, team_id = src["game_id"], src["team_id"]
        schedule = schedule_map.get(game_id)
        if schedule is None:
            raise ValueError(f"Team-box game is absent from schedule: {game_id}")
        sides = team_by_game[game_id]
        side = sides.get(team_id)
        if side is None:
            raise ValueError(f"Team-box team is not a scheduled participant: {game_id}/{team_id}")
        if side["side"] == "home":
            points_scored, points_allowed = schedule["home_score"], schedule["away_score"]
        else:
            points_scored, points_allowed = schedule["away_score"], schedule["home_score"]
        third_made, third_att = pair_values(src.get("thirdDownEff"), "-")
        fourth_made, fourth_att = pair_values(src.get("fourthDownEff"), "-")
        comp, pass_att = pair_values(src.get("completionAttempts"), "/")
        penalties, penalty_yards = pair_values(src.get("totalPenaltiesYards"), "-")
        possession = text(src.get("possessionTime"))
        possession_seconds = ""
        if possession and ":" in possession:
            mm, ss = possession.split(":", 1)
            try:
                possession_seconds = str(int(mm) * 60 + int(ss))
            except ValueError:
                possession_seconds = ""
        row = {
            "game_id": game_id, "season": src["season"], "week": schedule["week"],
            "season_type": schedule["season_type"], "game_date": schedule["game_date"],
            "team_id": team_id, "team": side["team"], "division": side["division"],
            "team_abbreviation": src.get("team_abbreviation") or side["abbr"],
            "opponent_team_id": side["opponent_id"], "opponent": side["opponent"],
            "opponent_division": side["opponent_division"],
            "home_away": side["side"], "points_scored": points_scored,
            "points_allowed": points_allowed, "first_downs": src.get("firstDowns", ""),
            "total_yards": src.get("totalYards", ""), "net_passing_yards": src.get("netPassingYards", ""),
            "completions": number_string(comp), "passing_attempts": number_string(pass_att),
            "yards_per_pass": src.get("yardsPerPass", ""), "rushing_yards": src.get("rushingYards", ""),
            "rushing_attempts": src.get("rushingAttempts", ""),
            "yards_per_rush_attempt": src.get("yardsPerRushAttempt", ""),
            "third_down_conversions": number_string(third_made), "third_down_attempts": number_string(third_att),
            "third_down_pct": number_string(ratio(third_made, third_att, percent=True)),
            "fourth_down_conversions": number_string(fourth_made), "fourth_down_attempts": number_string(fourth_att),
            "fourth_down_pct": number_string(ratio(fourth_made, fourth_att, percent=True)),
            "penalties": number_string(penalties), "penalty_yards": number_string(penalty_yards),
            "turnovers": src.get("turnovers", ""), "fumbles_lost": src.get("fumblesLost", ""),
            "interceptions_thrown": src.get("interceptions", ""),
            "possession_time": possession, "possession_seconds": possession_seconds,
        }
        team_game_map[(game_id, team_id)] = row
    team_games = list(team_game_map.values())

    # FBS browser datasets are filtered views of the complete source tables.
    fbs_players = [row for row in players if row["division"] == "FBS"]
    fbs_player_games = [row for row in player_games if row["division"] == "FBS"]
    fbs_player_seasons = [row for row in player_seasons if row["division"] == "FBS"]
    fbs_games = [
        row for row in games
        if row["home_division"] == "FBS" or row["away_division"] == "FBS"
    ]
    fbs_team_games = [row for row in team_games if row["division"] == "FBS"]

    # Read the immutable AP poll snapshot collected from ESPN's documented
    # weekly rankings endpoint. Keep ESPN poll-period labels distinct from
    # schedule-week applicability (preseason is not relabeled as Poll Week 1).
    with AP_RANKINGS_SOURCE.open(encoding="utf-8") as handle:
        ap_source = json.load(handle)
    if ap_source.get("season") != 2025:
        raise ValueError("AP rankings source is not the 2025 season")
    ap_source_polls = ap_source.get("polls", [])
    expected_ap_scopes = {
        ("preseason", 1), *(("regular", week) for week in range(2, 17)), ("postseason", 1),
    }
    actual_ap_scopes = {
        (text(poll.get("season_type")), int(poll.get("week_index", 0)))
        for poll in ap_source_polls
    }
    if actual_ap_scopes != expected_ap_scopes or len(ap_source_polls) != 17:
        raise ValueError(f"Unexpected AP poll coverage: {sorted(actual_ap_scopes)}")

    def parse_espn_team_id(team_ref: str) -> str:
        match = re.search(r"/teams/(\d+)(?:\?|$)", text(team_ref))
        if not match:
            raise ValueError(f"Could not read ESPN team ID from ranking team reference: {team_ref}")
        return match.group(1)

    schedule_days_by_week: dict[int, list[str]] = defaultdict(list)
    for src in schedule_rows:
        if text(src.get("season_type")) == "2" and text(src.get("week")):
            schedule_days_by_week[int(src["week"])].append(text(src.get("game_date"))[:10])

    ap_periods: list[dict[str, Any]] = []
    ap_rank_rows: list[dict[str, Any]] = []
    ap_rank_map_by_period: list[dict[str, int]] = []
    ap_poll_validation: list[dict[str, Any]] = []
    source_previous_rank_mismatches = 0
    for period_index, item in enumerate(
        sorted(ap_source_polls, key=lambda value: text(value.get("poll", {}).get("date"))), start=1,
    ):
        poll = item["poll"]
        stage = text(item.get("season_type"))
        if text(poll.get("type")) != "ap" or text(poll.get("name")) != "AP Top 25":
            raise ValueError(f"Non-AP rankings record in AP source: {poll.get('name')}/{poll.get('type')}")
        occurrence = poll.get("occurrence") or {}
        poll_label = text(occurrence.get("displayValue"))
        poll_week = ""
        effective_schedule_week = ""
        if stage == "regular":
            week_match = re.fullmatch(r"Week\s+(\d+)", poll_label)
            if not week_match:
                raise ValueError(f"Unexpected regular AP poll label: {poll_label}")
            poll_week = int(week_match.group(1))
            if poll_week not in range(2, 17):
                raise ValueError(f"Regular AP poll week out of expected range: {poll_week}")
            previous_days = schedule_days_by_week.get(poll_week - 1, [])
            current_days = schedule_days_by_week.get(poll_week, [])
            poll_day = text(poll.get("date"))[:10]
            if not previous_days or not current_days:
                raise ValueError(f"Schedule lacks dates to validate AP poll week {poll_week}")
            if not (max(previous_days) <= poll_day < min(current_days)):
                raise ValueError(
                    f"AP Week {poll_week} date {poll_day} does not fall after Week {poll_week - 1} "
                    f"and before Week {poll_week} games"
                )
            effective_schedule_week = poll_week
        elif stage == "preseason":
            first_week_days = schedule_days_by_week.get(1, [])
            if not first_week_days or text(poll.get("date"))[:10] >= min(first_week_days):
                raise ValueError("Preseason AP snapshot is not dated before the first scheduled game")
            if poll_label != "Preseason":
                raise ValueError(f"Unexpected preseason AP poll label: {poll_label}")
            effective_schedule_week = 1
        elif stage == "postseason":
            if poll_label != "Final Rankings":
                raise ValueError(f"Unexpected postseason AP poll label: {poll_label}")
        else:
            raise ValueError(f"Unexpected AP season type: {stage}")

        poll_date = text(poll.get("date"))[:10]
        source_rank_map: dict[str, int] = {}
        rank_values: list[int] = []
        poll_team_ids: set[str] = set()
        for source_rank in poll.get("ranks", []):
            team_id = parse_espn_team_id((source_rank.get("team") or {}).get("$ref", ""))
            if team_id not in team_brand_by_id:
                raise ValueError(f"Ranked team ID {team_id} missing from team_branding.json")
            if team_id in poll_team_ids:
                raise ValueError(f"Duplicate AP team in {poll_label}: team_id={team_id}")
            poll_team_ids.add(team_id)
            rank = int(source_rank["current"])
            rank_values.append(rank)
            source_rank_map[team_id] = rank
            brand = team_brand_by_id[team_id]
            previous_number = decimal_value(source_rank.get("previous"))
            previous_rank = int(previous_number) if previous_number is not None and previous_number > 0 else ""
            rank_change = previous_rank - rank if previous_rank != "" else ""
            record = (source_rank.get("record") or {}).get("summary", "")
            ap_rank_rows.append({
                "season": 2025, "poll_stage": stage, "poll_week": poll_week,
                "effective_schedule_week": effective_schedule_week, "poll_order": period_index,
                "poll_label": poll_label, "poll_date": poll_date, "rank": rank,
                "team_id": team_id, "team_name": brand["team_name"],
                "team_abbreviation": brand.get("abbreviation", ""),
                "division": division_by_team_id[team_id], "conference": brand.get("conference", ""),
                "previous_rank": previous_rank, "rank_change": rank_change,
                "first_place_votes": number_string(decimal_value(source_rank.get("firstPlaceVotes"))),
                "poll_points": number_string(decimal_value(source_rank.get("points"))),
                "record": record,
            })
        if len(poll_team_ids) != 25:
            raise ValueError(f"AP {poll_label} has {len(poll_team_ids)} ranked teams, expected 25")
        if any(rank < 1 or rank > 25 for rank in rank_values):
            raise ValueError(f"AP {poll_label} has a rank outside 1–25")
        duplicate_rank_values = sorted(rank for rank, count in Counter(rank_values).items() if count > 1)

        previous_poll_map = ap_rank_map_by_period[-1] if ap_rank_map_by_period else {}
        if ap_rank_map_by_period:
            for row in poll.get("ranks", []):
                team_id = parse_espn_team_id((row.get("team") or {}).get("$ref", ""))
                source_prev = decimal_value(row.get("previous"))
                source_prev_rank = int(source_prev) if source_prev is not None and source_prev > 0 else None
                expected_prev_rank = previous_poll_map.get(team_id)
                if source_prev_rank != expected_prev_rank:
                    source_previous_rank_mismatches += 1

        period = {
            "season": 2025, "poll_stage": stage, "poll_week": poll_week,
            "effective_schedule_week": effective_schedule_week, "poll_order": period_index,
            "poll_label": poll_label, "poll_date": poll_date,
            "source_date": text(poll.get("date")), "rank_map": source_rank_map,
        }
        ap_periods.append(period)
        ap_rank_map_by_period.append(source_rank_map)
        ap_poll_validation.append({
            "poll_stage": stage, "poll_week": poll_week, "effective_schedule_week": effective_schedule_week,
            "poll_label": poll_label, "poll_date": poll_date, "ranked_teams": len(poll_team_ids),
            "unique_team_ids": len(poll_team_ids), "duplicate_rank_values": duplicate_rank_values,
        })

    # Dense team-period timeline: unranked teams retain blank rank and an
    # explicit is_ranked=false value so entrants and departures are observable.
    trend_rows: list[dict[str, Any]] = []
    prior_rank_map: dict[str, int] = {}
    weeks_ranked: Counter[str] = Counter()
    best_rank: dict[str, int] = {}
    for period in ap_periods:
        current_rank_map = period["rank_map"]
        for team_id in sorted(team_brand_by_id, key=lambda value: int(value)):
            brand = team_brand_by_id[team_id]
            rank = current_rank_map.get(team_id)
            previous_rank = prior_rank_map.get(team_id)
            if period["effective_schedule_week"] and rank is not None:
                weeks_ranked[team_id] += 1
            if rank is not None:
                best_rank[team_id] = min(best_rank.get(team_id, rank), rank)
            trend_rows.append({
                "season": 2025, "poll_stage": period["poll_stage"], "poll_week": period["poll_week"],
                "effective_schedule_week": period["effective_schedule_week"],
                "poll_order": period["poll_order"], "poll_label": period["poll_label"],
                "poll_date": period["poll_date"], "team_id": team_id,
                "team_name": brand["team_name"], "team_abbreviation": brand.get("abbreviation", ""),
                "division": division_by_team_id[team_id], "conference": brand.get("conference", ""),
                "is_ranked": str(rank is not None).lower(), "rank": rank if rank is not None else "",
                "previous_rank": previous_rank if previous_rank is not None else "",
                "rank_change": previous_rank - rank if previous_rank is not None and rank is not None else "",
                "entered_poll": "" if period["poll_order"] == 1 else str(rank is not None and previous_rank is None).lower(),
                "dropped_from_previous_poll": "" if period["poll_order"] == 1 else str(rank is None and previous_rank is not None).lower(),
                "weeks_ranked_to_date": weeks_ranked[team_id],
                "best_rank_to_date": best_rank.get(team_id, ""),
            })
        prior_rank_map = current_rank_map

    ap_rank_columns = [
        "season", "poll_stage", "poll_week", "effective_schedule_week", "poll_order",
        "poll_label", "poll_date", "rank", "team_id", "team_name", "team_abbreviation",
        "division", "conference", "previous_rank", "rank_change", "first_place_votes",
        "poll_points", "record",
    ]
    trend_columns = [
        "season", "poll_stage", "poll_week", "effective_schedule_week", "poll_order",
        "poll_label", "poll_date", "team_id", "team_name", "team_abbreviation",
        "division", "conference", "is_ranked", "rank", "previous_rank", "rank_change",
        "entered_poll", "dropped_from_previous_poll", "weeks_ranked_to_date", "best_rank_to_date",
    ]

    # Validate whole-source season and schedule scope.
    pbp_games: set[str] = set()
    pbp_rows = 0
    with INPUTS["pbp"].open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"game_id", "season", "week"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"PBP file lacks required columns: {sorted(missing)}")
        for row in reader:
            pbp_rows += 1
            pbp_games.add(text(row.get("game_id")))
    schedule_ids = set(schedule_map)
    player_game_ids = {row["game_id"] for row in player_games}
    team_game_ids = {row["game_id"] for row in team_games}
    pbp_only_games = sorted(pbp_games - schedule_ids)
    schedule_without_pbp = sorted(schedule_ids - pbp_games)

    # Key and coverage validation.
    player_game_duplicates = duplicate_count(player_games, ("game_id", "team_id", "athlete_id"))
    player_season_duplicates = duplicate_count(player_seasons, ("season", "team_id", "athlete_id"))
    team_game_duplicates_after = duplicate_count(team_games, ("game_id", "team_id"))
    team_rows_by_game = Counter(row["game_id"] for row in team_games)
    schedule_two_team_games = sum(team_rows_by_game[g] == 2 for g in schedule_ids)
    negative_counts = assert_nonnegative(player_games, [
        "passing_completions", "passing_attempts", "passing_touchdowns", "passing_interceptions",
        "rushing_attempts", "rushing_touchdowns", "receptions", "receiving_touchdowns",
        "fumbles", "fumbles_lost", "fumbles_recovered", "defensive_total_tackles",
        "defensive_solo_tackles", "defensive_sacks", "defensive_tackles_for_loss",
        "passes_defended", "quarterback_hurries", "defensive_touchdowns", "defensive_interceptions",
        "interception_touchdowns", "kick_returns", "kick_return_touchdowns", "punt_returns",
        "punt_return_touchdowns", "field_goals_made", "field_goal_attempts", "extra_points_made",
        "extra_point_attempts", "punts", "punt_touchbacks", "punts_inside_20",
    ])
    impossible_completions = sum(
        (decimal_value(row.get("passing_completions")) or Decimal(0))
        > (decimal_value(row.get("passing_attempts")) or Decimal(0))
        for row in player_games
        if text(row.get("passing_attempts"))
    )
    impossible_fg = sum(
        (decimal_value(row.get("field_goals_made")) or Decimal(0))
        > (decimal_value(row.get("field_goal_attempts")) or Decimal(0))
        for row in player_games if text(row.get("field_goal_attempts"))
    )
    impossible_xp = sum(
        (decimal_value(row.get("extra_points_made")) or Decimal(0))
        > (decimal_value(row.get("extra_point_attempts")) or Decimal(0))
        for row in player_games if text(row.get("extra_point_attempts"))
    )

    # Cross-check every aggregate field against an independent second pass over
    # the generated player-game rows.
    game_sums: dict[tuple[str, str, str], dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for row in player_games:
        key = (row["season"], row["team_id"], row["athlete_id"])
        for field in SUM_FIELDS:
            value = decimal_value(row.get(field))
            if value is not None:
                game_sums[key][field] += value
    season_map = {(r["season"], r["team_id"], r["athlete_id"]): r for r in player_seasons}
    season_sum_mismatches: list[dict[str, str]] = []
    for key, summed in game_sums.items():
        season_row = season_map[key]
        for field in SUM_FIELDS:
            actual = decimal_value(season_row.get(field)) or Decimal(0)
            if actual != summed[field]:
                season_sum_mismatches.append({"season": key[0], "team_id": key[1], "athlete_id": key[2], "field": field})
    if season_sum_mismatches:
        raise ValueError(f"Season aggregation mismatch: {len(season_sum_mismatches)} values")

    # Reproducible random audit: 3 distinct teams per role bucket when available.
    randomizer = random.Random(2025)
    position_buckets = {
        "QB": ("QB", "passing"), "RB": ("RB", "rushing"), "WR": ("WR", "receiving"),
        "TE": ("TE", "receiving"), "OL_identity_only": ("OL", None),
        "defensive_DL": ("DL", "defensive"), "defensive_LB": ("LB", "defensive"),
        "defensive_DB": ("DB", "defensive"), "kicker": ("PK", "kicking"), "punter": ("P", "punting"),
    }
    categories_by_key: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for src in player_box_rows:
        categories_by_key[(src["season"], src["team_id"], src["athlete_id"])].add(src["category"])
    random_audit: list[dict[str, Any]] = []
    for bucket, (abbr, expected_category) in position_buckets.items():
        candidates = [r for r in roster_rows if r.get("position_abbreviation") == abbr]
        if expected_category:
            candidates = [r for r in candidates if expected_category in categories_by_key.get((r["season"], r["team_id"], r["athlete_id"]), set())]
        by_team: dict[str, list[dict[str, str]]] = defaultdict(list)
        for candidate in candidates:
            by_team[candidate["team_id"]].append(candidate)
        teams = sorted(by_team)
        randomizer.shuffle(teams)
        picks: list[dict[str, str]] = []
        for team_id in teams[:3]:
            picks.append(randomizer.choice(by_team[team_id]))
        checks: list[dict[str, Any]] = []
        for pick in picks:
            key = (pick["season"], pick["team_id"], pick["athlete_id"])
            pb_rows = [r for r in player_box_rows if (r["season"], r["team_id"], r["athlete_id"]) == key]
            roster_hit = roster_map.get(key) is not None
            name_ok = all(text(r.get("athlete_name")).casefold() == text(pick.get("full_name")).casefold() for r in pb_rows)
            category_ok = expected_category is None or expected_category in {r["category"] for r in pb_rows}
            checks.append({
                "athlete_id": pick["athlete_id"], "team_id": pick["team_id"],
                "roster_match": roster_hit, "has_player_box_rows": bool(pb_rows),
                "display_name_consistent": name_ok, "expected_category_present": category_ok,
                "passed": roster_hit and bool(pb_rows) and name_ok and category_ok,
            })
        random_audit.append({
            "bucket": bucket, "position_abbreviation": abbr,
            "sampled_players": len(picks), "distinct_teams": len({r["team_id"] for r in picks}),
            "checks_passed": sum(check["passed"] for check in checks), "checks_total": len(checks),
            "sample_results": checks,
            "check_types": ["season+team_id+athlete_id roster match", "display-name consistency", "expected stat category"],
        })

    position_counts: dict[str, dict[str, int]] = {}
    grouped_positions: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in roster_rows:
        grouped_positions[text(row.get("position_abbreviation")) or "(blank)"].append(row)
    for position, records in sorted(grouped_positions.items()):
        position_counts[position] = {
            "roster_team_entries": len(records),
            "distinct_athlete_ids": len({r["athlete_id"] for r in records}),
        }

    if player_game_duplicates or player_season_duplicates or team_game_duplicates_after:
        raise ValueError("Output duplicate-key validation failed")
    if player_game_ids - schedule_ids or team_game_ids - schedule_ids or pbp_only_games:
        raise ValueError("A source game ID did not join to the authoritative schedule")
    if schedule_two_team_games != len(schedule_ids):
        raise ValueError("Not every scheduled game has exactly two team-box rows")
    if any(negative_counts.values()) or impossible_completions or impossible_fg or impossible_xp:
        raise ValueError("Traditional-stat range validation failed; inspect source values")
    quality: dict[str, Any] = {
        "season": 2025,
        "sources": {
            str(path.relative_to(ROOT)): {"bytes": path.stat().st_size}
            for path in INPUTS.values()
        } | {str(TEAM_BRANDING.relative_to(ROOT)): {"bytes": TEAM_BRANDING.stat().st_size},
             str(AP_RANKINGS_SOURCE.relative_to(ROOT)): {"bytes": AP_RANKINGS_SOURCE.stat().st_size}},
        "row_counts": {
            "raw_play_by_play": pbp_rows, "schedule": len(schedule_rows),
            "player_box_category_rows": len(player_box_rows), "team_box_rows": len(team_box_rows),
            "roster_entries": len(roster_rows), "player_game_rows": len(player_games),
            "player_season_team_rows": len(player_seasons), "team_game_rows": len(team_games),
        },
        "join_coverage": {
            "player_box_rows_matching_roster_by_season_team_athlete": {
                "matched": roster_match_rows, "total": len(player_box_rows),
                "percent": round(roster_match_rows / len(player_box_rows) * 100, 4),
            },
            "unique_player_team_season_entities_matching_roster": {
                "matched": len(matched_player_box_entities), "total": len(player_box_unique_entities),
                "percent": round(len(matched_player_box_entities) / len(player_box_unique_entities) * 100, 4),
            },
            "scheduled_games_with_player_game_rows": {
                "matched": len(player_game_ids & schedule_ids), "total": len(schedule_ids),
                "percent": round(len(player_game_ids & schedule_ids) / len(schedule_ids) * 100, 4),
            },
            "scheduled_games_with_team_game_rows": {
                "matched": len(team_game_ids & schedule_ids), "total": len(schedule_ids),
                "percent": round(len(team_game_ids & schedule_ids) / len(schedule_ids) * 100, 4),
            },
            "play_by_play_games_in_schedule": {
                "matched": len(pbp_games & schedule_ids), "total": len(pbp_games),
                "percent": round(len(pbp_games & schedule_ids) / len(pbp_games) * 100, 4) if pbp_games else 100,
            },
        },
        "game_coverage": {
            "schedule_games": len(schedule_ids), "play_by_play_games": len(pbp_games),
            "schedule_games_without_play_by_play": schedule_without_pbp,
            "play_by_play_games_missing_schedule": pbp_only_games,
            "schedule_rows_without_player_game_rows": sorted(schedule_ids - player_game_ids),
        },
        "roster_position_quality": {
            "position_counts": position_counts,
            "blank_position_entries": sum(not text(r.get("position_abbreviation")) for r in roster_rows),
            "unknown_position_entries": len(unknown_roster_entries),
            "unknown_position_keys": unknown_roster_entries,
            "player_box_athlete_ids_without_roster_match": sorted(player_box_ids_without_roster),
            "unmatched_player_box_row_count": len(player_box_unmatched),
            "unmatched_player_box_keys": player_box_unmatched,
            "matched_entities_with_name_mismatch": len(name_mismatch_entities),
        },
        "passing_normalization": {
            "normalized_passing_rows": sum(r["category"] == "passing" for r in player_box_rows) - len(passing_unmapped),
            "unmapped_generic_stat_rows": len(passing_unmapped),
            "mapping_decision": "Not mapped: stat_1..stat_5 never overlap the normalized passing fields, so their meaning cannot be verified from this file alone.",
            "unmapped_rows": passing_unmapped,
        },
        "duplicate_key_checks": {
            "roster_season_team_athlete": roster_duplicates,
            "player_box_game_team_athlete_category": player_box_duplicates,
            "player_game_game_team_athlete": player_game_duplicates,
            "player_season_season_team_athlete": player_season_duplicates,
            "schedule_game_id": schedule_duplicates,
            "team_game_game_team": team_game_duplicates_after,
            "team_games_with_exactly_two_rows": schedule_two_team_games,
            "scheduled_games": len(schedule_ids),
        },
        "stat_validation": {
            "negative_count_statistics": negative_counts,
            "completions_exceed_attempts": impossible_completions,
            "field_goals_made_exceed_attempts": impossible_fg,
            "extra_points_made_exceed_attempts": impossible_xp,
            "season_totals_match_sum_of_player_game_rows": True,
            "season_total_value_mismatches": 0,
        },
        "coverage": {
            "weeks": sorted({int(r["week"]) for r in schedule_rows if text(r.get("week"))}),
            "season_types": sorted({r["season_type"] for r in schedule_rows}),
            "unique_schedule_teams": len({r["home_id"] for r in schedule_rows} | {r["away_id"] for r in schedule_rows}),
            "unique_roster_athletes": len({r["athlete_id"] for r in roster_rows}),
            "unique_player_box_athletes": len({r["athlete_id"] for r in player_box_rows}),
        },
        "division_classification": {
            "source": str(TEAM_BRANDING.relative_to(ROOT)),
            "teams_by_division": dict(Counter(division_by_team_id.values())),
            "fbs_players": len(fbs_players),
            "fbs_player_game_rows": len(fbs_player_games),
            "fbs_player_season_rows": len(fbs_player_seasons),
            "games_with_at_least_one_fbs_team": len(fbs_games),
            "fbs_team_game_rows": len(fbs_team_games),
            "fbs_players_by_position": dict(Counter(
                text(r.get("position_abbreviation")) or "(blank)" for r in fbs_players
            )),
            "fbs_players_with_unknown_position": sum(r["position_known"] != "true" for r in fbs_players),
            "unmapped_passing_rows_for_fbs_quarterbacks": sum(
                row["passing_normalization_status"] == "generic_fields_unmapped"
                and row["division"] == "FBS" and row["position_abbreviation"] == "QB"
                for row in player_games
            ),
            "fbs_key_duplicates": {
                "players_season_team_athlete": duplicate_count(fbs_players, ("season", "team_id", "athlete_id")),
                "player_games_game_team_athlete": duplicate_count(fbs_player_games, ("game_id", "team_id", "athlete_id")),
                "player_seasons_season_team_athlete": duplicate_count(fbs_player_seasons, ("season", "team_id", "athlete_id")),
                "games_game_id": duplicate_count(fbs_games, ("game_id",)),
                "team_games_game_team": duplicate_count(fbs_team_games, ("game_id", "team_id")),
            },
        },
        "ap_top25": {
            "source": str(AP_RANKINGS_SOURCE.relative_to(ROOT)),
            "source_description": ap_source.get("source"),
            "source_coverage_note": ap_source.get("coverage_note"),
            "unavailable_scopes": ap_source.get("unavailable_scopes", []),
            "poll_count": len(ap_periods),
            "ranked_team_poll_rows": len(ap_rank_rows),
            "all_ranked_team_ids_match_branding": True,
            "source_previous_rank_mismatches_vs_prior_captured_poll": source_previous_rank_mismatches,
            "polls": ap_poll_validation,
            "trend_rows": len(trend_rows),
            "trend_team_poll_duplicates": duplicate_count(trend_rows, ("poll_order", "team_id")),
        },
        "random_join_audit_seed": 2025,
        "random_join_audit": random_audit,
        "notes": [
            "Player-box generic passing stat_1..stat_5 values are preserved but not interpreted because the file does not label them and they do not overlap normalized passing fields.",
            "The roster position '-' is retained and flagged as unknown; no position is inferred.",
            "Player-box rows absent from the roster retain their IDs and statistics with blank position and roster_match=false.",
            "Team box does not contain sacks allowed, tackles for loss allowed, or offensive-line grades.",
            "Two schedule games have no rows in the existing play-by-play file; schedule and box-score records remain available for them.",
        ],
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "players_2025.csv", player_columns, players, overwrite=overwrite)
    write_csv(OUT / "player_game_stats_2025.csv", player_game_columns, player_games, overwrite=overwrite)
    write_csv(OUT / "player_season_stats_2025.csv", season_columns, player_seasons, overwrite=overwrite)
    write_csv(OUT / "games_2025.csv", game_columns, games, overwrite=overwrite)
    write_csv(OUT / "team_game_stats_2025.csv", team_game_columns, team_games, overwrite=overwrite)
    write_csv(OUT / "fbs_players_2025.csv", player_columns, fbs_players, overwrite=overwrite)
    write_csv(OUT / "fbs_player_game_stats_2025.csv", player_game_columns, fbs_player_games, overwrite=overwrite)
    write_csv(OUT / "fbs_player_season_stats_2025.csv", season_columns, fbs_player_seasons, overwrite=overwrite)
    write_csv(OUT / "fbs_games_2025.csv", game_columns, fbs_games, overwrite=overwrite)
    write_csv(OUT / "fbs_team_game_stats_2025.csv", team_game_columns, fbs_team_games, overwrite=overwrite)
    write_csv(OUT / "ap_top25_2025.csv", ap_rank_columns, ap_rank_rows, overwrite=overwrite)
    write_csv(OUT / "ap_top25_trends_2025.csv", trend_columns, trend_rows, overwrite=overwrite)
    quality["outputs"] = {
        name: {"rows": rows, "columns": len(columns), "bytes": (OUT / name).stat().st_size}
        for name, rows, columns in [
            ("players_2025.csv", len(players), player_columns),
            ("player_game_stats_2025.csv", len(player_games), player_game_columns),
            ("player_season_stats_2025.csv", len(player_seasons), season_columns),
            ("games_2025.csv", len(games), game_columns),
            ("team_game_stats_2025.csv", len(team_games), team_game_columns),
            ("fbs_players_2025.csv", len(fbs_players), player_columns),
            ("fbs_player_game_stats_2025.csv", len(fbs_player_games), player_game_columns),
            ("fbs_player_season_stats_2025.csv", len(fbs_player_seasons), season_columns),
            ("fbs_games_2025.csv", len(fbs_games), game_columns),
            ("fbs_team_game_stats_2025.csv", len(fbs_team_games), team_game_columns),
            ("ap_top25_2025.csv", len(ap_rank_rows), ap_rank_columns),
            ("ap_top25_trends_2025.csv", len(trend_rows), trend_columns),
        ]
    }
    quality_path = OUT / "player_data_quality_2025.json"
    with quality_path.open("w" if overwrite else "x", encoding="utf-8") as handle:
        json.dump(quality, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    # Re-read emitted CSVs and validate their actual written record/key totals.
    reread_expectations = {
        "players_2025.csv": (len(players), ("season", "team_id", "athlete_id")),
        "player_game_stats_2025.csv": (len(player_games), ("game_id", "team_id", "athlete_id")),
        "player_season_stats_2025.csv": (len(player_seasons), ("season", "team_id", "athlete_id")),
        "games_2025.csv": (len(games), ("game_id",)),
        "team_game_stats_2025.csv": (len(team_games), ("game_id", "team_id")),
        "fbs_players_2025.csv": (len(fbs_players), ("season", "team_id", "athlete_id")),
        "fbs_player_game_stats_2025.csv": (len(fbs_player_games), ("game_id", "team_id", "athlete_id")),
        "fbs_player_season_stats_2025.csv": (len(fbs_player_seasons), ("season", "team_id", "athlete_id")),
        "fbs_games_2025.csv": (len(fbs_games), ("game_id",)),
        "fbs_team_game_stats_2025.csv": (len(fbs_team_games), ("game_id", "team_id")),
        "ap_top25_2025.csv": (len(ap_rank_rows), ("poll_order", "team_id")),
        "ap_top25_trends_2025.csv": (len(trend_rows), ("poll_order", "team_id")),
    }
    for filename, (expected_rows, key_columns) in reread_expectations.items():
        written = read_csv(OUT / filename)
        if len(written) != expected_rows:
            raise ValueError(f"Written row count mismatch for {filename}")
        if duplicate_count(written, key_columns):
            raise ValueError(f"Written duplicate keys found in {filename}")

    for name in OUTPUT_NAMES:
        path = OUT / name
        print(f"{path.relative_to(ROOT)}\t{path.stat().st_size} bytes")
    print(f"player_game_rows={len(player_games)} player_season_rows={len(player_seasons)} games={len(games)} team_game_rows={len(team_games)}")
    print(f"unmapped_passing_rows={len(passing_unmapped)} roster_match={roster_match_rows}/{len(player_box_rows)} ({roster_match_rows / len(player_box_rows) * 100:.2f}%)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
