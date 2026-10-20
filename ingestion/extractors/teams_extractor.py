import pandas as pd
import logging
from nba_api.stats.static import teams

logger = logging.getLogger(__name__)

class TeamsExtractor:
    """Extractor for NBA teams data from the nba_api static module."""

    def extract(self):
        """
        Extract all NBA teams from the nba_api static module.
        Returns a DataFrame with one row per team.
        No API call required since this is static data.
        """
        normalized_columns = {
            "id": "TEAM_ID",
            "full_name": "FULL_NAME",
            "abbreviation": "ABBREVIATION",
            "nickname": "NICKNAME",
            "city": "CITY",
            "state": "STATE",
            "year_founded": "YEAR_FOUNDED"
        }
        logger.info("Extracting teams data from nba_api static module")
        
        teams_data = teams.get_teams()
        df = pd.DataFrame(teams_data)
        df = df.rename(columns=normalized_columns)
        logger.info(f"Extracted {len(df)} teams")
        return df