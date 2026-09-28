#!/usr/bin/env python3
"""Build static ESPN team branding metadata for teams in the dashboard data."""

from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REFERENCE_URL = (
    "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/"
    "espn_cfb_teams/cfb_teams_2025.csv"
)


def main() -> None:
    with urllib.request.urlopen(REFERENCE_URL, timeout=60) as response:
        reference_rows = list(csv.DictReader(line.decode("utf-8") for line in response))
    teams_used: set[str] = set()
    with (DATA / "cfb_pbp_2025_dashboard.csv").open(newline="", encoding="utf-8") as source:
        for row in csv.DictReader(source):
            teams_used.add(row["pos_team"].strip())
            teams_used.add(row["def_pos_team"].strip())

    result: dict[str, dict[str, str]] = {}
    for row in reference_rows:
        name = row.get("display_name", "").strip()
        if name not in teams_used:
            continue
        result[name] = {
            "id": row.get("team_id", ""),
            "abbreviation": row.get("abbreviation", ""),
            "shortName": row.get("short_display_name", ""),
            "logo": row.get("team_logo", ""),
            "logoDark": row.get("team_logo_dark", ""),
            "primaryColor": "#" + row["color"].strip().lstrip("#") if row.get("color", "").strip() else "",
            "secondaryColor": "#" + row["alternate_color"].strip().lstrip("#") if row.get("alternate_color", "").strip() else "",
            "conference": row.get("conference_name", ""),
            "division": row.get("division", ""),
        }

    missing = sorted(teams_used - result.keys())
    if missing:
        print(f"No branding metadata found for {len(missing)} teams; the site will use initials fallbacks.")
    output = {
        "source": REFERENCE_URL,
        "sourceDescription": "SportsDataverse ESPN college football teams reference, season 2025.",
        "generatedFromSeason": 2025,
        "teams": result,
    }
    (DATA / "team_branding.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote data/team_branding.json with {len(result)} of {len(teams_used)} dashboard teams.")


if __name__ == "__main__":
    main()
