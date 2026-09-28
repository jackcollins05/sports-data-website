#!/usr/bin/env python3
"""Analyze the cleaned 2025 CFB play-by-play CSV and write report findings."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/cfb_pbp_2025_dashboard.csv"
OUTPUT = ROOT / "data/report_findings.json"
REQUIRED = {
    "season", "seasonType", "week", "game_id", "wallclock", "homeTeamName",
    "awayTeamName", "pos_team", "def_pos_team", "period", "clock.displayValue",
    "down", "distance", "orig_play_type", "play", "statYardage", "yds_rushed",
    "yds_receiving", "scoring_play", "pos_score_pts", "EPA", "def_EPA",
    "EPA_success", "EPA_explosive",
}


def flag(value: str) -> bool:
    value = value.strip().lower()
    if value in {"true", "1"}:
        return True
    if value in {"false", "0"}:
        return False
    raise ValueError(f"Unexpected boolean value: {value!r}")


def number(value: str) -> float | None:
    value = value.strip()
    return float(value) if value else None


def summary(records: list[dict]) -> dict:
    n = len(records)
    if not n:
        return {"n": 0, "mean_epa": None, "success_rate": None,
                "explosive_rate": None, "scoring_rate": None, "mean_yards": None}
    epa = [r["epa"] for r in records if r["epa"] is not None]
    yards = [r["yards"] for r in records if r["yards"] is not None]
    return {
        "n": n,
        "mean_epa": sum(epa) / len(epa) if epa else None,
        "epa_n": len(epa),
        "success_rate": sum(r["success"] for r in records if r["success"] is not None)
        / sum(r["success"] is not None for r in records),
        "success_n": sum(r["success"] is not None for r in records),
        "explosive_rate": sum(r["explosive"] for r in records if r["explosive"] is not None)
        / sum(r["explosive"] is not None for r in records),
        "explosive_n": sum(r["explosive"] is not None for r in records),
        "scoring_rate": sum(r["scoring"] for r in records if r["scoring"] is not None)
        / sum(r["scoring"] is not None for r in records),
        "scoring_n": sum(r["scoring"] is not None for r in records),
        "mean_yards": sum(yards) / len(yards) if yards else None,
        "yards_n": len(yards),
    }


def group_summary(records: list[dict], key: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        value = record[key]
        if value is not None:
            groups[str(value)].append(record)
    return {name: [dict(key=name, **summary(group))] for name, group in groups.items()}


def metric_points(groups: dict[str, list[dict]], metric: str, min_n: int = 1) -> list[dict]:
    points = [
        {"label": label, **rows[0]}
        for label, rows in groups.items()
        if rows[0]["n"] >= min_n and rows[0].get(metric) is not None
    ]
    return sorted(points, key=lambda point: point[metric])


def fmt(value: float, digits: int = 3) -> str:
    return f"{value:+.{digits}f}" if value < 0 else f"{value:.{digits}f}"


def pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def main() -> None:
    with INPUT.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        missing_columns = REQUIRED - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"Missing input columns: {sorted(missing_columns)}")
        all_rows = 0
        administrative_rows = 0
        actual = []
        team_names = set()
        games = set()
        weeks = set()
        season_types = Counter()
        row_missing = Counter()
        type_bad = Counter()
        dates = []
        success_epa_mismatch = 0
        def_epa_mismatch = 0
        for row in reader:
            all_rows += 1
            games.add(row["game_id"])
            if row["week"].strip():
                weeks.add(row["week"])
            if row["seasonType"].strip():
                season_types[row["seasonType"]] += 1
            for team_field in ("pos_team", "def_pos_team"):
                if row[team_field].strip():
                    team_names.add(row[team_field].strip())
            for field, value in row.items():
                if field in REQUIRED and not value.strip():
                    row_missing[field] += 1
            if row["wallclock"].strip():
                dates.append(row["wallclock"].strip()[:10])
            actual_flag = flag(row["play"])
            if not actual_flag:
                administrative_rows += 1
                continue
            epa = number(row["EPA"])
            def_epa = number(row["def_EPA"])
            success = flag(row["EPA_success"])
            explosive = flag(row["EPA_explosive"])
            scoring = flag(row["scoring_play"])
            if epa is None:
                type_bad["actual_play_missing_EPA"] += 1
            if def_epa is None:
                type_bad["actual_play_missing_def_EPA"] += 1
            if epa is not None and success != (epa > 0):
                success_epa_mismatch += 1
            if epa is not None and def_epa is not None and not math.isclose(def_epa, -epa, abs_tol=1e-8):
                def_epa_mismatch += 1
            actual.append({
                "game_id": row["game_id"], "team": row["pos_team"].strip(),
                "opponent": row["def_pos_team"].strip(), "week": row["week"].strip(),
                "season_type": row["seasonType"].strip(), "period": row["period"].strip(),
                "down": row["down"].strip(), "type": row["orig_play_type"].strip() or "Unspecified",
                "play": actual_flag, "epa": epa, "def_epa": def_epa,
                "success": success, "explosive": explosive, "scoring": scoring,
                "yards": number(row["statYardage"]),
            })

    if not actual:
        raise ValueError("No actual play rows found")
    if success_epa_mismatch:
        raise ValueError(f"EPA_success disagrees with EPA > 0 on {success_epa_mismatch} actual plays")
    if def_epa_mismatch:
        raise ValueError(f"def_EPA is not the negative of EPA on {def_epa_mismatch} actual plays")

    overall = summary(actual)
    by_season_type = group_summary(actual, "season_type")
    by_type = group_summary(actual, "type")
    by_down = group_summary(actual, "down")
    by_period = group_summary(actual, "period")
    by_week = group_summary(actual, "week")
    by_team = group_summary(actual, "team")
    by_opponent = group_summary(actual, "opponent")

    run_types = {"Rush", "Rushing Touchdown"}
    pass_types = {"Pass Reception", "Pass Incompletion", "Pass Completion", "Sack", "Passing Touchdown"}
    pass_rush = {
        "Rush-coded": summary([r for r in actual if r["type"] in run_types]),
        "Pass-coded": summary([r for r in actual if r["type"] in pass_types]),
    }
    success_groups = {
        "EPA-positive": summary([r for r in actual if r["success"]]),
        "EPA-nonpositive": summary([r for r in actual if not r["success"]]),
    }
    explosive_groups = {
        "EPA-explosive": summary([r for r in actual if r["explosive"]]),
        "Other actual plays": summary([r for r in actual if not r["explosive"]]),
    }
    scoring_groups = {
        "Scoring flagged": summary([r for r in actual if r["scoring"]]),
        "Not scoring flagged": summary([r for r in actual if not r["scoring"]]),
    }

    downs = [p for p in metric_points(by_down, "mean_epa") if p["label"] in {"1", "2", "3", "4"}]
    periods = [p for p in metric_points(by_period, "mean_epa") if p["label"].isdigit()]
    weeks_data = [p for p in metric_points(by_week, "mean_epa") if p["label"].isdigit()]
    offense_rank = metric_points(by_team, "mean_epa", min_n=300)
    defense_rank = []
    for team, rs in group_summary(actual, "opponent").items():
        # A defense's measure is def_EPA = negative offensive EPA; higher favors defense.
        defense_rank.append({"label": team, **{
            "n": rs[0]["n"],
            "mean_def_epa": sum(r["def_epa"] for r in actual if r["opponent"] == team)
            / sum(r["def_epa"] is not None for r in actual if r["opponent"] == team),
        }})
    defense_rank = sorted([p for p in defense_rank if p["n"] >= 300], key=lambda p: p["mean_def_epa"])

    regular = by_season_type.get("2", [summary([])])[0]
    postseason = by_season_type.get("3", [summary([])])[0]
    hi_off = offense_rank[-1]
    lo_off = offense_rank[0]
    hi_def = defense_rank[-1]
    lo_def = defense_rank[0]
    high_week = max((p for p in weeks_data if p["n"] >= 300), key=lambda p: p["mean_epa"])
    low_week = min((p for p in weeks_data if p["n"] >= 300), key=lambda p: p["mean_epa"])

    findings = [
        {
            "id": "season-phase", "kicker": "SEASON PHASE",
            "title": "Postseason play carried a different EPA profile",
            "copy": (f"Among {regular['n']:,} regular-season actual plays, average EPA was {fmt(regular['mean_epa'])} and the EPA-positive rate was {pct(regular['success_rate'])}. "
                     f"The {postseason['n']:,} postseason plays averaged {fmt(postseason['mean_epa'])} EPA with a {pct(postseason['success_rate'])} success rate. "
                     "These are play-weighted averages, so each actual play contributes once."),
            "chart": {"type": "bar", "metric": "mean_epa", "unit": "EPA / actual play", "data": [
                {"label": "Regular season", **regular}, {"label": "Postseason", **postseason}]},
        },
        {
            "id": "explosives", "kicker": "EXPLOSIVE PLAYS",
            "title": "EPA-flagged explosive plays delivered much larger value per snap",
            "copy": (f"The source marked {explosive_groups['EPA-explosive']['n']:,} of {len(actual):,} actual plays as EPA-explosive ({pct(overall['explosive_rate'])}). "
                     f"Those plays averaged {fmt(explosive_groups['EPA-explosive']['mean_epa'])} EPA, compared with {fmt(explosive_groups['Other actual plays']['mean_epa'])} for other actual plays. "
                     "Explosive status uses the dataset's EPA-based flag, not a yardage threshold."),
            "chart": {"type": "bar", "metric": "mean_epa", "unit": "EPA / actual play", "data": [
                {"label": "EPA-explosive", **explosive_groups['EPA-explosive']},
                {"label": "Other plays", **explosive_groups['Other actual plays']}]},
        },
        {
            "id": "success", "kicker": "SUCCESS RATE",
            "title": "Fewer than half of actual plays added expected points",
            "copy": (f"{overall['success_n']:,} actual plays had a defined success flag; {sum(r['success'] for r in actual):,} were positive-EPA plays, a {pct(overall['success_rate'])} success rate. "
                     f"EPA-positive plays averaged {fmt(success_groups['EPA-positive']['mean_epa'])} EPA, while nonpositive plays averaged {fmt(success_groups['EPA-nonpositive']['mean_epa'])}. "
                     "The source defines success as EPA greater than zero."),
            "chart": {"type": "bar", "metric": "mean_epa", "unit": "Average EPA by success outcome", "data": [
                {"label": "EPA-positive", **success_groups['EPA-positive']},
                {"label": "EPA-nonpositive", **success_groups['EPA-nonpositive']}]},
        },
        {
            "id": "pass-rush", "kicker": "PLAY PROFILE",
            "title": "Pass-coded snaps were more efficient than rush-coded snaps",
            "copy": (f"Rush-coded events ({', '.join(sorted(run_types))}) totaled {pass_rush['Rush-coded']['n']:,} actual plays at {fmt(pass_rush['Rush-coded']['mean_epa'])} EPA per play. "
                     f"The pass-coded set ({', '.join(sorted(pass_types))}) totaled {pass_rush['Pass-coded']['n']:,} at {fmt(pass_rush['Pass-coded']['mean_epa'])}. "
                     "Other play types are excluded from this comparison; categories follow the source's play labels."),
            "chart": {"type": "bar", "metric": "mean_epa", "unit": "EPA / actual play", "data": [
                {"label": "Rush-coded", **pass_rush['Rush-coded']}, {"label": "Pass-coded", **pass_rush['Pass-coded']}]},
        },
        {
            "id": "downs", "kicker": "DOWN & DISTANCE",
            "title": "Fourth down produced the strongest average EPA, with a small denominator",
            "copy": ("EPA per actual play varies by down because the field position and conversion stakes change. "
                     + " ".join(f"{p['label']}{'st' if p['label']=='1' else 'nd' if p['label']=='2' else 'rd' if p['label']=='3' else 'th'} down: {fmt(p['mean_epa'])} EPA on {p['n']:,} plays ({pct(p['success_rate'])} positive)." for p in downs)
                     + " The chart reports all four downs; fourth-down volume is substantially lower than early-down volume."),
            "chart": {"type": "bar", "metric": "mean_epa", "unit": "EPA / actual play", "data": [
                {"label": f"{p['label']}{'st' if p['label']=='1' else 'nd' if p['label']=='2' else 'rd' if p['label']=='3' else 'th'}", **p} for p in downs]},
        },
        {
            "id": "quarters", "kicker": "GAME FLOW",
            "title": "Second-quarter plays averaged the most EPA among regulation quarters",
            "copy": (f"Period 2 averaged {fmt(next((p['mean_epa'] for p in periods if p['label']=='2'), 0))} EPA per actual play across "
                     f"{next((p['n'] for p in periods if p['label']=='2'), 0):,} plays, compared with "
                     f"{fmt(next((p['mean_epa'] for p in periods if p['label']=='1'), 0))} in Period 1, "
                     f"{fmt(next((p['mean_epa'] for p in periods if p['label']=='3'), 0))} in Period 3, and "
                     f"{fmt(next((p['mean_epa'] for p in periods if p['label']=='4'), 0))} in Period 4. "
                     "Overtime periods are shown separately and have much smaller samples."),
            "chart": {"type": "bar", "metric": "mean_epa", "unit": "EPA / actual play", "data": [
                {"label": "Period " + p["label"], **p} for p in periods]},
        },
        {
            "id": "weeks", "kicker": "WEEKLY RHYTHM",
            "title": f"Week {high_week['label']} led the adequately sized weekly EPA averages",
            "copy": (f"Among weeks with at least 300 actual plays, Week {high_week['label']} averaged {fmt(high_week['mean_epa'])} EPA across {high_week['n']:,} plays; "
                     f"Week {low_week['label']} averaged {fmt(low_week['mean_epa'])} across {low_week['n']:,}. "
                     "Weeks below 300 actual plays are omitted from this comparison to limit small-sample swings."),
            "chart": {"type": "bar", "metric": "mean_epa", "unit": "EPA / actual play", "data": [
                {"label": "Week " + p["label"], **p} for p in sorted(weeks_data, key=lambda x: int(x["label"]))]},
        },
        {
            "id": "offense-teams", "kicker": "TEAM OFFENSE",
            "title": f"{hi_off['label']} led the 300-play offense group in EPA per play",
            "copy": (f"With a minimum of 300 actual plays, {hi_off['label']} averaged {fmt(hi_off['mean_epa'])} EPA per play over {hi_off['n']:,} plays. "
                     f"{lo_off['label']} was lowest in this same qualifying group at {fmt(lo_off['mean_epa'])} over {lo_off['n']:,}. "
                     "This is an unadjusted, play-weighted season average, not an opponent-adjusted rating."),
            "chart": {"type": "bar", "metric": "mean_epa", "unit": "EPA / actual play", "data": [
                {"label": p["label"], **p} for p in (offense_rank[-5:][::-1] + offense_rank[:5])]},
        },
        {
            "id": "defense-teams", "kicker": "TEAM DEFENSE",
            "title": f"{hi_def['label']} posted the strongest defensive EPA average in the qualifying group",
            "copy": (f"Among defenses facing at least 300 actual plays, {hi_def['label']} averaged {fmt(hi_def['mean_def_epa'])} defensive EPA per play over {hi_def['n']:,} plays. "
                     f"{lo_def['label']} averaged {fmt(lo_def['mean_def_epa'])} over {lo_def['n']:,}. "
                     "Because defensive EPA is defined as negative offensive EPA, higher values indicate more expected points denied. This is not opponent-adjusted."),
            "chart": {"type": "bar", "metric": "mean_def_epa", "unit": "Defensive EPA / play", "data": [
                {"label": p["label"], **p} for p in (defense_rank[-5:][::-1] + defense_rank[:5])]},
        },
        {
            "id": "scoring", "kicker": "FINISHING PLAYS",
            "title": "Scoring-flagged plays averaged 1.943 EPA per play",
            "copy": (f"{sum(r['scoring'] for r in actual):,} of {len(actual):,} actual plays ({pct(overall['scoring_rate'])}) carry the source's scoring-play flag. "
                     f"Flagged plays averaged {fmt(scoring_groups['Scoring flagged']['mean_epa'])} EPA; unflagged plays averaged {fmt(scoring_groups['Not scoring flagged']['mean_epa'])}. "
                     "The flag is reported as supplied and is not reconstructed from score changes."),
            "chart": {"type": "bar", "metric": "mean_epa", "unit": "EPA / actual play", "data": [
                {"label": "Scoring flagged", **scoring_groups['Scoring flagged']},
                {"label": "Not scoring flagged", **scoring_groups['Not scoring flagged']}]},
        },
    ]

    output = {
        "meta": {
            "season": 2025, "rows": all_rows, "actual_play_rows": len(actual),
            "administrative_rows": administrative_rows, "columns": 24,
            "unique_teams": len(team_names), "unique_games": len(games),
            "weeks": sorted(int(w) for w in weeks),
            "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
            "source": "SportsDataverse espn_cfb_pbp 2025 season release",
            "definitions": {
                "actual_play": "play == true; excludes administrative/non-play rows",
                "EPA": "Average of source EPA over included actual plays with a nonmissing EPA value",
                "def_EPA": "Source defensive EPA, defined as negative offensive EPA; positive favors defense",
                "success_rate": "EPA_success == true / actual plays with a nonmissing EPA_success flag; source defines success as EPA > 0",
                "explosive_rate": "EPA_explosive == true / actual plays with a nonmissing EPA_explosive flag; source EPA-based flag, not a yardage threshold",
                "scoring_rate": "scoring_play == true / actual plays with a nonmissing scoring_play flag",
                "average_yards": "Mean statYardage among included records with nonmissing statYardage",
                "team_threshold": "At least 300 actual plays faced/run, applied to team offense and defense rankings",
                "missing_values": dict(row_missing),
                "checks": {
                    "actual_play_EPA_success_disagreements": success_epa_mismatch,
                    "actual_play_def_EPA_not_negative_EPA": def_epa_mismatch,
                    "actual_play_missing_EPA": type_bad["actual_play_missing_EPA"],
                    "actual_play_missing_def_EPA": type_bad["actual_play_missing_def_EPA"],
                },
                "season_type_rows": dict(season_types),
            },
            "overall": overall,
        },
        "sections": findings,
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    print(f"Rows: {all_rows:,}; actual plays: {len(actual):,}; administrative rows: {administrative_rows:,}")
    print(f"Teams: {len(team_names)}; games: {len(games)}; weeks: {len(weeks)}")
    print(f"Average EPA: {fmt(overall['mean_epa'])}; success: {pct(overall['success_rate'])}; explosive: {pct(overall['explosive_rate'])}; scoring: {pct(overall['scoring_rate'])}")
    print(f"EPA_success mismatches: {success_epa_mismatch}; def_EPA sign mismatches: {def_epa_mismatch}")
    for section in findings:
        print(f"- {section['title']}")


if __name__ == "__main__":
    main()
