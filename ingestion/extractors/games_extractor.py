import pandas as pd
from nba_api.stats.endpoints import LeagueGameFinder
from config import settings as conf_settings

import re
import time
import logging
logger = logging.getLogger(__name__)

class GamesStatsExtractor:
    """Extractor for NBA games data using the nba_api LeagueGameFinder endpoint."""

    required_columns = [
        "GAME_ID", "TEAM_ID", "SEASON_ID", "TEAM_ABBREVIATION", "TEAM_NAME",
        "GAME_DATE", "MATCHUP", "WL", "MIN", "PTS", "FGM", "FGA", "FG_PCT",
        "FG3M", "FG3A", "FG3_PCT", "FTM", "FTA", "FT_PCT", "OREB", "DREB",
        "REB", "AST", "STL", "BLK", "TOV", "PF", "PLUS_MINUS"
    ]

    def __init__(self):
        self.timeout = conf_settings.NBA_API_TIMEOUT
        self.retries = conf_settings.NBA_API_TIMEOUT_RETRIES


    def extract(self, season_id):
        """
        Extract game stats for a given season using the LeagueGameFinder endpoint.
        Returns a DataFrame with one row per team per game.
        """
        logger.info(f"Extracting game stats for season {season_id} from nba_api LeagueGameFinder endpoint")

        if not re.match(r"^\d{4}-\d{2}$", season_id):
            raise ValueError(
                f"Invalid season_id format: '{season_id}'. "
                f"Expected format: '2024-25'"
            )
        
        
        # Retry the API call on any exception, up to self.retries times.
        attempt = 0
        while True:
            attempt += 1
            try:
                game_finder = LeagueGameFinder(season_nullable=season_id, timeout=self.timeout)
                games_data = game_finder.get_normalized_dict()
                break
            except Exception as exc:
                if attempt >= self.retries:
                    logger.error(
                        "Failed to fetch game stats for season %s after %s retries — skipping. Error: %s",
                        season_id, self.retries, exc
                    )
                    time.sleep(conf_settings.NBA_API_SLEEP * 5)
                    return pd.DataFrame(columns=self.required_columns)
                logger.warning(
                    "Attempt %s/%s failed: %s. Retrying after %s seconds.",
                    attempt, self.retries, exc, conf_settings.NBA_API_SLEEP,
                )
                time.sleep(conf_settings.NBA_API_SLEEP)

        # Sleep after successful API call to avoid hitting rate limits
        time.sleep(conf_settings.NBA_API_SLEEP)
        
        # The game stats data is in the 'LeagueGameFinderResults' key of the response
        games_df = pd.DataFrame(games_data['LeagueGameFinderResults'], columns=self.required_columns)

        # Regular season SEASON_ID starts with '2', preseason starts with '1'
        games_df = games_df[games_df["SEASON_ID"].str.startswith("2")]

        #Dropping duplicates based on GAME_ID and TEAM_ID
        games_df = games_df.drop_duplicates(subset=["GAME_ID", "TEAM_ID"], keep="last")
        logger.info(f"Extracted {len(games_df)} game stats rows for season {season_id}")
        return games_df