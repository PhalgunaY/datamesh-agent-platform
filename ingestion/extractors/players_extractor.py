import pandas as pd
from nba_api.stats.endpoints import CommonAllPlayers
from config import settings as conf_settings

import time
import logging

logger = logging.getLogger(__name__)

class PlayersExtractor:
    """Extractor for NBA players data using the nba_api CommonAllPlayers endpoint."""

    required_columns = [
        "PERSON_ID", "DISPLAY_LAST_COMMA_FIRST", "DISPLAY_FIRST_LAST", "ROSTERSTATUS", "FROM_YEAR", "TO_YEAR",
        "TEAM_ID", "TEAM_NAME", "TEAM_ABBREVIATION", "GAMES_PLAYED_FLAG"
    ]

    def __init__(self):
        self.timeout = conf_settings.NBA_API_TIMEOUT
        self.retries = conf_settings.NBA_API_TIMEOUT_RETRIES

    def extract(self):
        """
        Extract all NBA players using the CommonAllPlayers endpoint.
        Returns a DataFrame with one row per player.
        """
        logger.info("Extracting players data from nba_api CommonAllPlayers endpoint")

        # Columns intentionally excluded from CommonAllPlayers response:
        # - PLAYER_SLUG: internal API identifier, not used downstream
        # - TEAM_CODE: redundant with TEAM_ABBREVIATION
        # - OTHERLEAGUE_EXPERIENCE_CH: not relevant for NBA analysis
        
        # Retry the API call on any exception, up to self.retries times.
        attempt = 0
        while True:
            attempt += 1
            try:
                players_data = CommonAllPlayers(is_only_current_season=0, timeout=self.timeout).get_normalized_dict()
                break
            except Exception as exc:
                if attempt >= self.retries:
                    logger.exception("Failed to fetch players data after %s retries", self.retries)
                    raise
                logger.warning(
                    "Attempt %s/%s failed: %s. Retrying after %s seconds.",
                    attempt,
                    self.retries,
                    exc,
                    conf_settings.NBA_API_SLEEP,
                )
                time.sleep(conf_settings.NBA_API_SLEEP)

        # Sleep after successful API call to avoid hitting rate limits
        time.sleep(conf_settings.NBA_API_SLEEP)
        
        # The player data is in the 'CommonAllPlayers' key of the response
        players_df = pd.DataFrame(players_data['CommonAllPlayers'], columns=self.required_columns)
        logger.info(f"Extracted {len(players_df)} players")
        return players_df