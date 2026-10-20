# tests/extractors/test_teams_extractor.py

import pytest
import pandas as pd
from ingestion.extractors.teams_extractor import TeamsExtractor


class TestTeamsExtractor:

    def setup_method(self):
        """Runs before each test method."""
        self.extractor = TeamsExtractor()

    def test_extract_returns_dataframe(self):
        """extract() should return a pandas DataFrame."""
        result = self.extractor.extract()
        assert isinstance(result, pd.DataFrame)

    def test_extract_returns_thirty_teams(self):
        """NBA has exactly 30 teams — static data should always return 30."""
        result = self.extractor.extract()
        assert len(result) == 30

    def test_extract_contains_required_columns(self):
        """DataFrame must contain all columns defined in the Bronze schema."""
        required_columns = ["TEAM_ID", "FULL_NAME", "ABBREVIATION", "NICKNAME", 
                           "CITY", "STATE", "YEAR_FOUNDED"]
        result = self.extractor.extract()
        for col in required_columns:
            assert col in result.columns, f"Missing column: {col}"

    def test_team_id_is_unique(self):
        """TEAM_ID must be unique — it's the primary merge key."""
        result = self.extractor.extract()
        assert result["TEAM_ID"].nunique() == len(result)

    def test_no_null_team_ids(self):
        """Primary key column must never be null."""
        result = self.extractor.extract()
        assert result["TEAM_ID"].isnull().sum() == 0