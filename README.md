# Gridiron Pulse — Explore the 2025 College Football Season

Gridiron Pulse is a static, browser-based exploration of the 2025 NCAA Division I Football Bowl Subdivision (FBS) season. The project pairs an editorial season report with an interactive FBS Explorer for team performance, players, games, and official AP Top 25 polls. The report and dashboard run from prepared files in this repository; no server-side application or private key is required after deployment.

## Site pages

- [`index.html`](index.html) — the season report: five verified headline metrics, 11 data-backed findings with visualizations, and methodology notes.
- [`dashboard.html`](dashboard.html) — the FBS Explorer: game/week/team filters, team and player measures, player leaderboards and details, Team Room, conference measure rank, game results, AP poll board and ranking timeline, and an interactive FBS geography map.

The two pages share the layout and design system in `css/styles.css`. Browser requests use paths relative to the repository root, so the pages can be hosted at `https://jackcollins05.github.io/sports-data-website/`. Run a local static server only for local preview (instructions below); the deployed website needs no Python server or backend.

## Scope and data sources

The current report and dashboard focus on FBS teams and players for the 2025 season. FBS teams' games against FCS opponents remain in the schedule when at least one team is FBS. Team divisions come from the prepared ESPN/SportsDataverse team metadata and are not inferred from school names.

The prepared data in `data/football_2025/` is based on the project's downloaded 2025 files from these public sources:

- **Player game box scores:** SportsDataverse [`espn_cfb_player_box`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_cfb_player_box), joined with its [`espn_cfb_rosters`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_cfb_rosters) roster source for names, positions, jersey numbers, and headshots.
- **Schedules and final scores:** SportsDataverse [`espn_cfb_schedules`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_cfb_schedules).
- **Team game statistics:** SportsDataverse [`espn_cfb_team_box`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_cfb_team_box).
- **Team metadata and branding:** SportsDataverse [`espn_cfb_teams`](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_cfb_teams), prepared as [`data/team_branding.json`](data/team_branding.json). It contains ESPN team IDs, names, abbreviations, conferences, divisions, colors, and ESPN-hosted logo URLs.
- **AP Top 25:** historical AP poll records retrieved from ESPN's college football rankings feed using the cfbfastR/SportsDataverse rankings documentation ([cfbfastR manual](https://sportsdataverse.r-universe.dev/cfbfastR/doc/manual.html)). The prepared files retain the AP poll's preseason, regular poll, and final snapshots; the project does not create its own rankings or substitute CFP rankings. The 2025 source has no normal poll after schedule Week 1. The first available regular poll is source-labeled Week 2 and is shown to users as “After Week 1”; later labels follow the same convention. Preseason and Final remain distinct periods.
- **School geography:** stadium/campus coordinates from the [NCAA football stadium dataset](https://github.com/gboeing/data-visualization/tree/main/ncaa-football-stadiums), joined to the project team metadata by ESPN team ID and stored in [`team_geography_2025.json`](data/football_2025/team_geography_2025.json). Coordinates are stadium or campus locations; the file documents two approximate fallbacks.
- **State boundaries:** the locally bundled [`us_states.geojson`](data/football_2025/us_states.geojson), sourced from the [PublicaMundi MappingAPI US states GeoJSON](https://github.com/PublicaMundi/MappingAPI/blob/master/data/geojson/us-states.json). The interactive map uses this local geometry and local team coordinates; it does not call a map service or load map tiles.

The upstream providers publish season data and may revise files over time. The raw downloads used for this project are kept locally under `raw_data/` and are intentionally ignored by Git. The public site uses the prepared data files in `data/`; it does not fetch from `raw_data/` and does not need access to that folder.

## Data preparation and reproducibility

`scripts/prepare_football_data.py` reads the source schedule, player box, team box, roster, AP poll JSON, original play-by-play, and checked-in team metadata from their documented local paths under `raw_data/` and `data/`. It writes all-division and FBS-filtered tables, AP poll snapshots/trends, and a data-quality report into `data/football_2025/`. It preserves identifiers as strings, joins on IDs, validates duplicates and coverage, and does not silently resolve the documented unmapped passing rows. The raw inputs are not modified by the script.

`scripts/build_fbs_report.py` reads the prepared FBS season, team-game, game, player, and AP files and reproducibly generates `data/football_2025/report_findings_2025.json`, the small payload used by the report page. Its metric choices, minimum-opportunity thresholds, and calculation details are included in that output and described in the report methodology. `scripts/build_team_branding.py`, `scripts/prepare_data.py`, and `scripts/analyze_data.py` support the earlier play-by-play project version and its retained legacy artifacts; they are not the current report's findings pipeline.

To reproduce the current derived data, first obtain the original source files from the links above and place them at the exact paths expected in `scripts/prepare_football_data.py` (including `raw_data/play_by_play_2025.csv` and the files in `raw_data/supporting_2025/`). Keep those raw files out of Git. Then run:

```sh
python3 scripts/prepare_football_data.py
python3 scripts/build_fbs_report.py
```

The preparation script refuses to overwrite existing generated outputs unless explicitly instructed. Review its options before regenerating data. `data/football_2025/player_data_quality_2025.json` records source/join coverage and known data-quality limitations.

## Main data files

Each row in a player game table is a player-team-game appearance; each row in a player season table is one player/team season stint. Each team-game row is one team in one game. Each schedule row is one game. AP snapshot rows represent one team in one actual poll period; ranking trend rows preserve ranked/unranked status across periods.

| File | Use |
|---|---|
| `data/football_2025/fbs_games_2025.csv` | FBS-involving schedule, dates, teams, scores, and results. |
| `data/football_2025/fbs_team_game_stats_2025.csv` | Traditional team statistics for each FBS team-game. |
| `data/football_2025/fbs_player_season_stats_2025.csv` | Season totals and recalculated rates for FBS player/team stints; primary source for season leaderboards. |
| `data/football_2025/fbs_players_2025.csv` | FBS roster identity, positions, jersey, headshot, and team metadata; loaded on demand for player presentation. |
| `data/football_2025/fbs_player_game_stats_2025.csv` | FBS player-game lines; approximately 16 MB and loaded only for week/season-type player-game exploration. |
| `data/football_2025/ap_top25_2025.csv` | Official AP Top 25 team rows for each available 2025 poll snapshot. |
| `data/football_2025/ap_top25_trends_2025.csv` | Team-by-poll ranked status, movement, weeks ranked, and best rank; supports timelines and entry/exit calculations. |
| `data/football_2025/team_geography_2025.json` | Coordinates and location/conference metadata for all 136 FBS programs. |
| `data/football_2025/us_states.geojson` | Local state polygons used by the interactive map. |
| `data/football_2025/report_findings_2025.json` | Small, reproducible headline/story/chart payload for the report page. |
| `data/football_2025/player_data_quality_2025.json` | Preparation diagnostics, match coverage, duplicate checks, and known limitations. |

The folder also retains complete all-division counterparts (`players_2025.csv`, `player_game_stats_2025.csv`, `player_season_stats_2025.csv`, `games_2025.csv`, and `team_game_stats_2025.csv`) for traceability and future analysis. The browser experience is FBS-focused and uses the FBS files listed above.

### Metric and data notes

- Traditional box-score values are reported source statistics. Rates in the prepared season file are recalculated from aggregate totals and opportunities rather than summed from per-game averages. Team rate measures likewise use total conversions divided by total attempts when the dashboard aggregates games.
- The AP ranking pages use only the supplied AP Top 25 snapshots. Unranked periods remain explicitly unranked; they are not assigned a fabricated rank of 26.
- The source contains 37 FCS quarterbacks with unresolved generic passing-category rows. None of the unresolved rows affect FBS quarterbacks; the primary FBS QB leaderboard excludes lines marked with unresolved passing games rather than guessing at field mappings. See the generated quality report for details.
- Roster positions and team identity are joined using athlete/team IDs. Players who changed teams remain distinct by team stint.
- FBS-only browser files are filtered using the division field in prepared team branding metadata. A schedule game remains when it involves at least one FBS program, while team-game and player files retain only FBS teams/players.

## Runtime libraries and external assets

- [Apache ECharts 5.6.0](https://echarts.apache.org/) provides interactive charts.
- [Papa Parse 5.4.1](https://www.papaparse.com/) parses prepared CSV files in the browser.
- Both libraries load over HTTPS from jsDelivr through `js/dependencies.js`, with bounded timeouts and visible failure handling. The live pages do not use web workers for CSV parsing.
- Google Fonts loads Barlow Condensed, Manrope, and DM Mono over HTTPS; local system font fallbacks are defined in CSS.
- Team logos and player headshots use the prepared ESPN URLs. If an image is unavailable, the interface falls back to initials or retains the surrounding team/player information.

The report loads only its compact JSON findings and team metadata. The dashboard loads its small schedule, team-game, player-season, AP, branding, and map data at startup. Player roster imagery and the larger player-game CSV are deferred until the related explorer area or filters need them. The legacy play-by-play CSV is retained in the repository from the earlier project version but is not fetched by either current page.

## Local preview

From the repository root:

```sh
python3 -m http.server 8000
```

Open <http://localhost:8000/> for the report and <http://localhost:8000/dashboard.html> for the FBS Explorer. A local static server is needed for local browser `fetch()` calls; GitHub Pages itself serves the same files as a static site. The CDN, Google Fonts, ESPN-hosted logos, and headshots require internet access, while the report data, prepared CSVs, and map geometry are bundled locally.

## Repository guide

| Path | Purpose |
|---|---|
| `.gitignore` | Excludes `raw_data/` and `.DS_Store`; raw source downloads are not part of deployment. |
| `index.html`, `dashboard.html` | The two public site pages: Season Report and FBS Explorer. |
| `css/styles.css` | Shared typography, colors, responsive layouts, accessibility states, map, report, chart, and dashboard styles. |
| `js/common.js` | Shared brand identity, formatting, escaping, and display helpers. |
| `js/boot-guard.js` | Surfaces script, promise, or slow initialization failures as visible page errors. |
| `js/dependencies.js` | Loads ECharts and Papa Parse over HTTPS and reports dependency failures. |
| `js/report.js` | Loads the report findings/branding data and renders its metrics, 11 story sections, and charts. |
| `js/dashboard.js` | Loads FBS data, initializes dashboard filters/charts, and renders rankings, map, team/player/game views. |
| `js/field.js` | Lightweight decorative report-hero field canvas with reduced-motion and visibility handling. |
| `data/football_2025/` | Prepared FBS and all-division datasets, official AP snapshots/trends, report JSON, data-quality report, geography metadata, and state polygons. |
| `data/team_branding.json` | Prepared team names, ESPN IDs, conferences/divisions, colors, and logo URLs. |
| `data/cfb_pbp_2025_dashboard.csv` | Legacy V1 play-by-play dashboard extract (166,053 rows, 24 columns; 31,782,613 bytes); retained but not loaded by the current site. |
| `data/report_findings.json` | Legacy V1 play-by-play/EPA report output; retained but not loaded by the current report. |
| `scripts/prepare_football_data.py` | Rebuilds the current player, team, game, FBS, AP, and data-quality outputs from local source files. |
| `scripts/build_fbs_report.py` | Rebuilds the current report findings JSON from prepared FBS tables. |
| `scripts/prepare_data.py` | Legacy V1 play-by-play cleaning script. |
| `scripts/analyze_data.py` | Legacy V1 play-by-play/EPA report analysis. |
| `scripts/build_team_branding.py` | Legacy branding preparation helper retained for reproducibility/history. |
| `raw_data/` | Local-only upstream source files; ignored by Git and never needed by the deployed static site. |

Design and analysis: Jack Collins. Data credits: ESPN and SportsDataverse; AP poll records are attributed to the AP through ESPN's historical rankings data; geography and boundary sources are linked above. Team names, logos, and other marks belong to their respective rights holders.
