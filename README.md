# Saturday Signal — 2025 College Football

Saturday Signal is a static, browser-based college football analytics project. It pairs an editorial report with an interactive dashboard built from SportsDataverse’s ESPN college football play-by-play data for the 2025 season.

## Pages

- `index.html` is the scrollable report, with ten data-backed findings, charts, and a methodology section.
- `dashboard.html` loads and filters the season data in the browser. It supports offense/defense perspective, team/week/play-type/season-type filters, a switchable measure and grouping, responsive charts, and an aggregated sortable/paginated table.

Both pages use the same navigation, typography, palette, and responsive design system. They use relative local paths and can be hosted as a static GitHub Pages site. GitHub Pages has not been enabled as part of this project work.

## Version 2 visual experience

The report opens with a full-height stadium-field scene, restrained light beams, and season totals. Its findings reveal once as they enter view; headline figures count toward their verified values unless reduced motion is enabled. The team-offense finding uses an interactive efficiency × EPA-explosive-rate map for the ten highest qualifying offensive EPA averages among teams with at least 300 actual plays. Dashed crosshairs mark the unweighted means across those ten teams. Hover or keyboard-focus a point to read the exact EPA, explosive rate, success rate, and play count.

The dashboard adds a broadcast-style team performance banner. Team selection changes the logo, primary/secondary branding accents, and filtered performance values while leaving the dark site palette in place. Existing static team metadata and initials fallback are retained. The CSV loading screen displays actual parsed-row progress; the dataset streams in 1 MiB chunks through Papa Parse without estimating progress. The hero field is static on mobile, and motion respects reduced-motion preferences.

## Data

### Source and row meaning

The source is the public [`espn_cfb_pbp` SportsDataverse release](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_cfb_pbp), specifically its 2025 season CSV. Its underlying play-by-play is ESPN data processed and published by SportsDataverse. **One source row represents one play record**; some rows represent administrative events rather than an actual play.

The downloaded raw CSV is 582,452,515 bytes (about 555 MB). It lives at `raw_data/play_by_play_2025.csv` locally and is intentionally excluded from Git by `.gitignore`. Do not remove the `raw_data/` ignore rule or commit the raw file. The website-ready CSV at `data/cfb_pbp_2025_dashboard.csv` retains all **166,053 rows** and the 24 fields documented in `scripts/prepare_data.py`; it is **31,782,613 bytes**. It covers weeks 1–16 and 236 distinct teams in the possession and defense fields. Its source timestamps span 2025-08-23 through 2026-01-20.

### Preparation and analysis

From the project root:

```sh
python3 scripts/prepare_data.py
python3 scripts/analyze_data.py
python3 scripts/build_team_branding.py
```

`prepare_data.py` selects the documented 24 dashboard columns, preserves every row, and writes the smaller CSV. It prints exact output counts and missing-cell summaries. `analyze_data.py` reads that cleaned CSV, validates boolean encodings and EPA relationships, calculates the report statistics, and writes `data/report_findings.json`. `build_team_branding.py` downloads the public 2025 team reference CSV and writes the compact static JSON used by the site. It needs internet access but no API key or secret.

The raw source is not bundled into Git, so reproducing the CSV requires obtaining the same public release file and placing it at the documented ignored path before running the preparation script. Analysis of report findings only requires the cleaned CSV.

## Metric definitions and denominators

- **Actual play:** `play == true`. This source flag marks actual plays versus administrative rows. Report averages/rates exclude the 18,079 administrative rows; the website CSV still preserves all 166,053 rows. The report denominator is 147,974 actual plays.
- **Offensive EPA per actual play:** arithmetic mean of `EPA` across included actual plays with a nonmissing EPA value. This is an unadjusted possession-team average across the source’s actual-play records, including actual special-teams events; it is not an opponent-adjusted rating or a scrimmage-only EPA statistic. The retained 24 columns do not include the source's separate `scrimmage_play` flag.
- **Defensive EPA per actual play:** arithmetic mean of `def_EPA` for actual plays faced by `def_pos_team`. The source defines `def_EPA` as negative offensive EPA, so a higher value indicates more expected points denied.
- **EPA success rate:** count of `EPA_success == true` divided by actual plays with a nonmissing flag. The source defines a successful play as EPA greater than zero. For defense, the dashboard reports the complement (EPA ≤ 0 allowed) as defensive stop rate.
- **EPA explosive-play rate:** count of `EPA_explosive == true` divided by actual plays with a nonmissing flag. This is the source’s EPA-based explosive flag, not a project-invented yardage threshold. In defensive perspective, the displayed share is the complement, or non-explosive share allowed.
- **Scoring-play rate:** count of `scoring_play == true` divided by actual plays with a nonmissing flag. In defensive perspective it represents opponents’ scoring-flag share.
- **Average recorded yards:** arithmetic mean of `statYardage` among included actual plays with a nonmissing value. The separate `yds_rushed` and `yds_receiving` fields are intentionally sparse because they apply to particular play types.
- **Play-type comparison:** rush-coded includes `Rush` and `Rushing Touchdown`; pass-coded includes `Pass Reception`, `Pass Incompletion`, `Pass Completion`, `Sack`, and `Passing Touchdown`. Other types are excluded from that comparison.
- **Team ranking sample minimum:** the report’s possession-team and defensive-team EPA comparisons include teams with at least 300 actual plays run or faced, respectively. Values are still unadjusted for opponent strength and are not causal claims.
- **Grouping rates:** each week/down/period/team/play-type measure uses the actual plays in that group as the denominator. Figures show play counts alongside rates/averages; overtime and low-volume late-week samples are clearly identified by their counts.

All retained flags, `EPA`, `def_EPA`, and `statYardage` are populated for the actual-play subset. The cleaned file contains 564 blank `wallclock` values, 25 unspecified `orig_play_type` values, 102,678 blank `yds_rushed` values, and 123,574 blank `yds_receiving` values. No rows are excluded during preparation. The raw season file’s (`game_id`, `game_play_number`) key is unique across all 166,053 rows.

## Team branding and credits

`data/team_branding.json` is generated from the season-2025 ESPN college football teams reference published in the [SportsDataverse `espn_cfb_teams` release](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_cfb_teams). It supplies canonical team names, abbreviations, conference/division labels, primary/secondary colors, and ESPN logo URLs. The static file contains branding for all 236 teams in the dashboard dataset. The dashboard falls back to team initials and the site palette when branding or a logo is unavailable. Logos remain hosted by ESPN; this student project does not claim ownership of team marks.

Play-by-play data and metadata credit: ESPN and SportsDataverse. Team logo assets credit: ESPN. Dashboard/report design and analysis: Jack Collins.

## Local preview

Run a small static server from the project root (opening HTML via `file://` will block local data fetches):

```sh
python3 -m http.server 8000
```

Then visit `http://localhost:8000/` for the report or `http://localhost:8000/dashboard.html` for the dashboard. The dashboard streams the approximately 31.8 MB cleaned CSV in 1 MiB chunks, then calculates filtered views in the browser. A network connection is required for the CDN chart/parser libraries, Google Fonts, and hosted team logos. If remote libraries fail, the dashboard displays a data-load error; unavailable logos use initials. No backend service is required.

## Libraries and visual assets

- [Apache ECharts 5.6.0](https://echarts.apache.org/) — interactive dashboard charts, loaded from jsDelivr on `dashboard.html` only.
- [Papa Parse 5.4.1](https://www.papaparse.com/) — streamed browser CSV parsing in 1 MiB chunks, loaded from jsDelivr on `dashboard.html` only.
- Google Fonts — Barlow Condensed (display), Manrope (body), and DM Mono (numeric labels).
- A small custom Canvas 2D stadium-field illustration runs behind the report hero. It is decorative, noninteractive, pauses outside the viewport, uses a low device-pixel ratio, and becomes static when reduced motion is requested; the report remains complete without it.

## Project file guide

| File | Purpose |
|---|---|
| `.gitignore` | Ignores the entire local `raw_data/` directory. |
| `README.md` | Project, metric, data-source, preview, and file documentation. |
| `index.html` | Editorial report/story page and methodology. |
| `dashboard.html` | Interactive analytics interface. |
| `css/styles.css` | Shared design tokens, layout, accessible focus treatment, charts, and responsive styles. |
| `js/common.js` | Shared number formatting, HTML escaping, and team initials helper. |
| `js/field.js` | Lightweight canvas field visual with reduced-motion and visibility handling. |
| `js/report.js` | Loads verified findings JSON and renders report cards, story index, scroll reveals, comparison charts, and the accessible team signal map. |
| `js/dashboard.js` | Chunked CSV loading, filters, aggregations, dashboard charts, team performance banner, loading feedback, and table behavior. |
| `data/cfb_pbp_2025_dashboard.csv` | All 166,053 source rows reduced to the 24 retained fields; 31,782,613 bytes. |
| `data/report_findings.json` | Machine-readable, script-generated report findings, chart data, definitions, and validation results. |
| `data/team_branding.json` | Static 2025 team names, colors, conference/division metadata, and logo URLs for 236 teams. |
| `scripts/prepare_data.py` | Reproducible 24-column data preparation script. |
| `scripts/analyze_data.py` | Recomputes report findings and validates source flag/EPA definitions against the cleaned CSV. |
| `scripts/build_team_branding.py` | Downloads the public team reference and builds static team branding metadata. |
| `raw_data/play_by_play_2025.csv` | Local raw source download; ignored by Git and not part of the website output. |
