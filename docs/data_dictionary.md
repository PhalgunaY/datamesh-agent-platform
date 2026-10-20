# Data Dictionary — Bronze Layer Iceberg Tables
### data-mesh-agent-pipeline

> **Layer:** Bronze (raw, no transformations)  
> **Format:** Apache Iceberg tables  
> **Environments:** Local Filesystem (dev) · AWS S3 + Glue Catalog (prod)

---

## Table Summary

| Table | Source | Primary / Composite Key | Partition Key | Type |
|---|---|---|---|---|
| `bronze_teams` | `nba_api.stats.static.teams` | `TEAM_ID` | None | Dimension |
| `bronze_players` | `CommonAllPlayers` | `PERSON_ID` | None | Dimension |
| `bronze_game_stats` | `LeagueGameFinder` | `GAME_ID + TEAM_ID` | `SEASON_ID` | Fact |
| `bronze_player_stats` | `PlayerCareerStats` | `PLAYER_ID + SEASON_ID + TEAM_ID` | `SEASON_ID` | Fact |

---

## bronze_teams

Static reference table for all 30 NBA teams. Sourced from the `nba_api` static module — no API call required.

- **Type:** Dimension
- **Source:** `nba_api.stats.static.teams`
- **Primary Key:** `TEAM_ID`
- **Partition Key:** None
- **Update Pattern:** Static — refreshed only when franchise data changes

| Column | Type | Nullable | Description |
|---|---|---|---|
| `TEAM_ID` | LONG | No | Unique NBA team identifier — primary key |
| `FULL_NAME` | STRING | No | Full team name (e.g. Los Angeles Lakers) |
| `ABBREVIATION` | STRING | No | Three-letter team code (e.g. LAL) |
| `NICKNAME` | STRING | No | Team nickname (e.g. Lakers) |
| `CITY` | STRING | No | City the team represents |
| `STATE` | STRING | Yes | US state |
| `YEAR_FOUNDED` | INTEGER | Yes | Year the franchise was established |

---

## bronze_players

All players active across any season in the configured range. Sourced via a single `CommonAllPlayers` API call.

- **Type:** Dimension
- **Source:** `CommonAllPlayers`
- **Primary Key:** `PERSON_ID`
- **Partition Key:** None
- **Update Pattern:** Full refresh per pipeline run

| Column | Type | Nullable | Description |
|---|---|---|---|
| `PERSON_ID` | LONG | No | Unique NBA player identifier — primary key |
| `DISPLAY_LAST_COMMA_FIRST` | STRING | No | Player name in Last, First format |
| `DISPLAY_FIRST_LAST` | STRING | Yes | Player name in First Last format |
| `ROSTERSTATUS` | INTEGER | No | Active roster status flag (1 = active) |
| `FROM_YEAR` | STRING | No | First season the player was active |
| `TO_YEAR` | STRING | No | Most recent season the player was active |
| `TEAM_ID` | LONG | Yes | Most recent team identifier |
| `TEAM_ABBREVIATION` | STRING | Yes | Most recent team abbreviation |
| `TEAM_NAME` | STRING | Yes | Most recent team name |
| `GAMES_PLAYED_FLAG` | STRING | Yes | Flag indicating games played |

---

## bronze_game_stats

One row per team per game. The primary fact table for team-level game performance. Partitioned by `SEASON_ID` for efficient season-scoped queries.

- **Type:** Fact
- **Source:** `LeagueGameFinder`
- **Composite Key:** `GAME_ID + TEAM_ID`
- **Partition Key:** `SEASON_ID`
- **Update Pattern:** Season-by-season chunked extraction; idempotent MERGE writes

> **Note:** Each game produces two rows — one per team — so `GAME_ID` alone is not unique.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `GAME_ID` | STRING | No | Unique game identifier — composite key pt.1 |
| `TEAM_ID` | LONG | No | NBA team identifier — composite key pt.2 |
| `SEASON_ID` | STRING | No | Season identifier (e.g. 2024-25) — partition key |
| `TEAM_ABBREVIATION` | STRING | No | Three-letter team code |
| `TEAM_NAME` | STRING | No | Full team name |
| `GAME_DATE` | DATE | No | Date the game was played |
| `MATCHUP` | STRING | No | Matchup string (e.g. LAL vs. BOS) |
| `WL` | STRING | Yes | Result — W (win) or L (loss) |
| `MIN` | INTEGER | Yes | Minutes played |
| `PTS` | INTEGER | Yes | Points scored |
| `FGM` | INTEGER | Yes | Field goals made |
| `FGA` | INTEGER | Yes | Field goals attempted |
| `FG_PCT` | FLOAT | Yes | Field goal percentage |
| `FG3M` | INTEGER | Yes | Three-point field goals made |
| `FG3A` | INTEGER | Yes | Three-point field goals attempted |
| `FG3_PCT` | FLOAT | Yes | Three-point field goal percentage |
| `FTM` | INTEGER | Yes | Free throws made |
| `FTA` | INTEGER | Yes | Free throws attempted |
| `FT_PCT` | FLOAT | Yes | Free throw percentage |
| `OREB` | INTEGER | Yes | Offensive rebounds |
| `DREB` | INTEGER | Yes | Defensive rebounds |
| `REB` | INTEGER | Yes | Total rebounds |
| `AST` | INTEGER | Yes | Assists |
| `STL` | INTEGER | Yes | Steals |
| `BLK` | INTEGER | Yes | Blocks |
| `TOV` | INTEGER | Yes | Turnovers |
| `PF` | INTEGER | Yes | Personal fouls |
| `PLUS_MINUS` | FLOAT | Yes | Plus/minus rating for the game |

---

## bronze_player_stats

Season-level aggregate statistics per player. One row per player per season. Covers player movement across teams — a player traded mid-season will have multiple rows for that season (one per team). Partitioned by `SEASON_ID`.

- **Type:** Fact
- **Source:** `PlayerCareerStats`
- **Composite Key:** `PLAYER_ID + SEASON_ID`
- **Partition Key:** `SEASON_ID`
- **Update Pattern:** Season-by-season chunked extraction; idempotent MERGE writes

> **Note:** A player traded mid-season will have multiple rows for that season — one per team. The composite key `PLAYER_ID + SEASON_ID` is therefore not strictly unique; a full unique key would be `PLAYER_ID + SEASON_ID + TEAM_ID`.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `PLAYER_ID` | LONG | No | Unique player identifier — composite key pt.1 |
| `SEASON_ID` | STRING | No | Season identifier — composite key pt.2 / partition key |
| `LEAGUE_ID` | STRING | Yes | League identifier |
| `TEAM_ID` | LONG | Yes | Team identifier for that season |
| `TEAM_ABBREVIATION` | STRING | Yes | Team abbreviation for that season |
| `PLAYER_AGE` | FLOAT | Yes | Player age during that season |
| `GP` | INTEGER | Yes | Games played |
| `GS` | INTEGER | Yes | Games started |
| `MIN` | FLOAT | Yes | Average minutes per game |
| `FGM` | FLOAT | Yes | Field goals made per game |
| `FGA` | FLOAT | Yes | Field goals attempted per game |
| `FG_PCT` | FLOAT | Yes | Field goal percentage |
| `FG3M` | FLOAT | Yes | Three-point field goals made per game |
| `FG3A` | FLOAT | Yes | Three-point field goals attempted per game |
| `FG3_PCT` | FLOAT | Yes | Three-point field goal percentage |
| `FTM` | FLOAT | Yes | Free throws made per game |
| `FTA` | FLOAT | Yes | Free throws attempted per game |
| `FT_PCT` | FLOAT | Yes | Free throw percentage |
| `OREB` | FLOAT | Yes | Offensive rebounds per game |
| `DREB` | FLOAT | Yes | Defensive rebounds per game |
| `REB` | FLOAT | Yes | Total rebounds per game |
| `AST` | FLOAT | Yes | Assists per game |
| `STL` | FLOAT | Yes | Steals per game |
| `BLK` | FLOAT | Yes | Blocks per game |
| `TOV` | FLOAT | Yes | Turnovers per game |
| `PF` | FLOAT | Yes | Personal fouls per game |
| `PTS` | FLOAT | Yes | Points per game |

---

## Table Relationships

| Relationship | Join Condition | Notes |
|---|---|---|
| `bronze_game_stats` → `bronze_teams` | `bronze_game_stats.TEAM_ID = bronze_teams.TEAM_ID` | Each game row links to one team |
| `bronze_player_stats` → `bronze_teams` | `bronze_player_stats.TEAM_ID = bronze_teams.TEAM_ID` | Player season row links to team played for |
| `bronze_player_stats` → `bronze_players` | `bronze_player_stats.PLAYER_ID = bronze_players.PERSON_ID` | Note mismatched column names across endpoints |
| `bronze_game_stats` → `bronze_player_stats` | `TEAM_ID + SEASON_ID` | Links team game performance to player season stats |

## Notes

### SEASON_ID Format Inconsistency

`SEASON_ID` format differs between endpoints in the raw NBA API response — `LeagueGameFinder` returns it as `22024` while `PlayerCareerStats` returns `2024-25`. This inconsistency is **preserved in the Bronze layer** and normalised in the Silver layer (M2). See ADR-003 for the reasoning.

### Iceberg MERGE Behaviour

All fact tables (`bronze_game_stats`, `bronze_player_stats`) use idempotent MERGE writes — re-running the pipeline for a season will update existing rows rather than duplicate them. Dimension tables (`bronze_teams`, `bronze_players`) are fully refreshed on each run.

---

*Last updated: 2026-03-30 · data-mesh-agent-pipeline · Bronze Layer*
