import pandas as pd
from nba_api.stats.endpoints import PlayerCareerStats
from config import settings as conf_settings
from requests.exceptions import ReadTimeout
from json import JSONDecodeError

import re
import time
import logging
logger = logging.getLogger(__name__)

class PlayersStatsExtractor:
    """Extractor for NBA player season stats using the nba_api PlayerCareerStats endpoint."""

    required_columns = [
        "PLAYER_ID", "SEASON_ID", "LEAGUE_ID", "TEAM_ID", "TEAM_ABBREVIATION", "PLAYER_AGE",
        "GP", "GS", "MIN", "FGM", "FGA", "FG_PCT", "FG3M", "FG3A", "FG3_PCT",
        "FTM", "FTA", "FT_PCT", "OREB", "DREB", "REB", "AST", "STL", "BLK", "TOV",
        "PF", "PTS"
    ]

    def __init__(self):
        self.timeout = conf_settings.NBA_API_TIMEOUT
        self.retries = conf_settings.NBA_API_TIMEOUT_RETRIES

    def extract(self, player_id, season_id=None):
        logger.info(
            "Extracting player stats for player_id=%s season_id=%s from nba_api PlayerCareerStats endpoint",
            player_id,
            season_id,
        )
        if season_id is not None and not re.match(r"^\d{4}-\d{2}$", season_id):
            raise ValueError(
                f"Invalid season_id format: '{season_id}'. Expected format: '2024-25'"
            )
        attempt = 0
        while True:
            attempt += 1
            try:
                career_stats = PlayerCareerStats(
                    player_id=player_id,
                    timeout=self.timeout
                )
                stats_data = career_stats.get_normalized_dict()
                break
            except KeyError as e:
                logger.warning(
                    "Player %s has no career stats data — skipping. Error: %s",
                    player_id, e
                )
                return pd.DataFrame(columns=self.required_columns)
            except ReadTimeout:
                if attempt >= self.retries:
                    logger.error(
                        "Timeout fetching player stats for player_id=%s after %s retries — skipping.",
                        player_id, self.retries
                    )
                    time.sleep(conf_settings.NBA_API_SLEEP * 5)
                    return pd.DataFrame(columns=self.required_columns)
                backoff = conf_settings.NBA_API_SLEEP * (2 ** attempt)
                logger.warning(
                    "Timeout on attempt %s/%s for player_id=%s — backing off %ss",
                    attempt, self.retries, player_id, backoff
                )
                time.sleep(backoff)
            except Exception as exc:
                if attempt >= self.retries:
                    logger.error(
                        "Failed to fetch player stats for player_id=%s after %s retries — skipping. Error: %s",
                        player_id, self.retries, exc
                    )
                    time.sleep(conf_settings.NBA_API_SLEEP * 5)
                    return pd.DataFrame(columns=self.required_columns)
                logger.warning(
                    "Attempt %s/%s failed: %s. Retrying after %s seconds.",
                    attempt, self.retries, exc, conf_settings.NBA_API_SLEEP,
                )
                time.sleep(conf_settings.NBA_API_SLEEP)

        time.sleep(conf_settings.NBA_API_SLEEP)
        player_stats = stats_data["SeasonTotalsRegularSeason"]
        player_stats_df = pd.DataFrame(player_stats, columns=self.required_columns)
        if season_id is not None:
            player_stats_df = player_stats_df[player_stats_df["SEASON_ID"] == season_id]
        logger.info(
            "Extracted %s player season stat rows for player_id=%s season_id=%s",
            len(player_stats_df),
            player_id,
            season_id,
        )
        return player_stats_df