#!/usr/bin/env python3
"""Create the compact 2025 college football play-by-play dashboard CSV."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


COLUMNS = [
    "season",
    "seasonType",
    "week",
    "game_id",
    "wallclock",
    "homeTeamName",
    "awayTeamName",
    "pos_team",
    "def_pos_team",
    "period",
    "clock.displayValue",
    "down",
    "distance",
    "orig_play_type",
    "play",
    "statYardage",
    "yds_rushed",
    "yds_receiving",
    "scoring_play",
    "pos_score_pts",
    "EPA",
    "def_EPA",
    "EPA_success",
    "EPA_explosive",
]

# Small enough to print all values. Team name fields are summarized by count
# and most common values so a run does not print hundreds of names.
VALUE_COUNT_FIELDS = ("seasonType", "week", "orig_play_type", "play")
TEAM_FIELDS = ("pos_team", "def_pos_team", "homeTeamName", "awayTeamName")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("raw_data/play_by_play_2025.csv"),
        help="raw input CSV (default: raw_data/play_by_play_2025.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/cfb_pbp_2025_dashboard.csv"),
        help="website-ready output CSV (default: data/cfb_pbp_2025_dashboard.csv)",
    )
    args = parser.parse_args()

    missing = Counter()
    value_counts = {column: Counter() for column in VALUE_COUNT_FIELDS}
    team_values = {column: Counter() for column in TEAM_FIELDS}
    rows = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.input.open("r", newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        absent = [column for column in COLUMNS if column not in (reader.fieldnames or [])]
        if absent:
            raise ValueError(f"Input is missing required columns: {', '.join(absent)}")

        with args.output.open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for row in reader:
                rows += 1
                selected = {column: row.get(column, "") or "" for column in COLUMNS}
                writer.writerow(selected)
                for column, value in selected.items():
                    if not value.strip():
                        missing[column] += 1
                for column, counts in value_counts.items():
                    counts[selected[column].strip() or "<MISSING>"] += 1
                for column, counts in team_values.items():
                    value = selected[column].strip()
                    if value:
                        counts[value] += 1

    print(f"Output: {args.output}")
    print(f"Rows: {rows:,}")
    print(f"Columns: {len(COLUMNS)}")
    print(f"File size: {args.output.stat().st_size:,} bytes")
    print("Missing values (blank cells):")
    for column in COLUMNS:
        print(f"  {column}: {missing[column]:,}")
    print("Categorical value counts:")
    for column, counts in value_counts.items():
        print(f"  {column} ({len(counts)} unique): {dict(counts.most_common())}")
    print("Team field coverage:")
    for column, counts in team_values.items():
        print(
            f"  {column}: {len(counts)} unique; "
            f"top 5 by row count: {counts.most_common(5)}"
        )


if __name__ == "__main__":
    main()
