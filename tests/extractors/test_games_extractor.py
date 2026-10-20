import pytest
import pandas as pd
from types import SimpleNamespace

import ingestion.extractors.games_extractor as games_module


class TestGamesStatsExtractor:

    def test_init_reads_settings(self, monkeypatch):
        monkeypatch.setattr(games_module.conf_settings, "NBA_API_TIMEOUT", 123)
        monkeypatch.setattr(games_module.conf_settings, "NBA_API_TIMEOUT_RETRIES", 5)

        extractor = games_module.GamesStatsExtractor()

        assert extractor.timeout == 123
        assert extractor.retries == 5

    def test_extract_returns_dataframe_on_success(self, monkeypatch):
        recorded_sleep = []

        def fake_sleep(seconds):
            recorded_sleep.append(seconds)

        class FakeLeagueGameFinder:
            def __init__(self, season_nullable, timeout):
                self.season_nullable = season_nullable
                self.timeout = timeout

            def get_normalized_dict(self):
                return {
                    "LeagueGameFinderResults": [
                        ["0022400001", 1610612747, "2024-25", "LAL", "Los Angeles Lakers", "2024-10-22", "LAL vs. DEN", "W", 240, 119, 45, 88, 0.511, 12, 32, 0.375, 17, 22, 0.773, 10, 35, 45, 28, 8, 5, 14, 18, 15.0],
                        ["0022400001", 1610612743, "2024-25", "DEN", "Denver Nuggets", "2024-10-22", "DEN @ LAL", "L", 240, 107, 40, 91, 0.440, 10, 28, 0.357, 17, 23, 0.739, 12, 32, 44, 25, 7, 4, 12, 19, -15.0],
                    ]
                }

        monkeypatch.setattr(games_module, "LeagueGameFinder", FakeLeagueGameFinder)
        monkeypatch.setattr(games_module.time, "sleep", fake_sleep)

        extractor = games_module.GamesStatsExtractor()
        result = extractor.extract("2024-25")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert result.iloc[0, 0] == "0022400001"
        assert recorded_sleep == [games_module.conf_settings.NBA_API_SLEEP]

    def test_extract_filters_preseason_games(self, monkeypatch):
        def fake_sleep(seconds):
            pass

        class FakeLeagueGameFinder:
            def __init__(self, season_nullable, timeout):
                self.season_nullable = season_nullable
                self.timeout = timeout

            def get_normalized_dict(self):
                return {
                    "LeagueGameFinderResults": [
                        ["0022400006", 1610612747, "2024-25", "LAL", "Los Angeles Lakers", "2024-10-26", "LAL vs. PHX", "W", 240, 119, 45, 88, 0.511, 12, 32, 0.375, 17, 22, 0.773, 10, 35, 45, 28, 8, 5, 14, 18, 15.0],
                        ["0012400001", 1610612747, "12024", "LAL", "Los Angeles Lakers", "2024-10-10", "LAL vs. PHX", "W", 240, 107, 40, 91, 0.440, 10, 28, 0.357, 17, 23, 0.739, 12, 32, 44, 25, 7, 4, 12, 19, -15.0],
                    ]
                }

        monkeypatch.setattr(games_module, "LeagueGameFinder", FakeLeagueGameFinder)
        monkeypatch.setattr(games_module.time, "sleep", fake_sleep)

        extractor = games_module.GamesStatsExtractor()
        result = extractor.extract("2024-25")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["SEASON_ID"] == "2024-25"
        assert not result["SEASON_ID"].str.startswith("1").any()

    def test_extract_retries_until_success(self, monkeypatch):
        sleep_calls = []
        call_number = {"count": 0}

        def fake_sleep(seconds):
            sleep_calls.append(seconds)

        class FakeLeagueGameFinder:
            def __init__(self, season_nullable, timeout):
                self.season_nullable = season_nullable
                self.timeout = timeout
                call_number["count"] += 1
                self.call_index = call_number["count"]

            def get_normalized_dict(self):
                if self.call_index < 3:
                    raise RuntimeError("temporary failure")
                return {
                    "LeagueGameFinderResults": [
                        ["0022400002", 1610612759, "2024-25", "SAS", "San Antonio Spurs", "2024-10-23", "SAS vs. DAL", "W", 240, 120, 46, 89, 0.517, 13, 33, 0.394, 15, 20, 0.750, 11, 36, 47, 29, 9, 6, 15, 20, 10.0]
                    ]
                }

        monkeypatch.setattr(games_module, "LeagueGameFinder", FakeLeagueGameFinder)
        monkeypatch.setattr(games_module.time, "sleep", fake_sleep)

        extractor = games_module.GamesStatsExtractor()
        extractor.retries = 3

        result = extractor.extract("2024-25")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert call_number["count"] == 3
        assert sleep_calls == [
            games_module.conf_settings.NBA_API_SLEEP,
            games_module.conf_settings.NBA_API_SLEEP,
            games_module.conf_settings.NBA_API_SLEEP,
        ]

    def test_extract_raises_after_max_retries(self, monkeypatch):
        sleep_calls = []
        call_number = {"count": 0}

        def fake_sleep(seconds):
            sleep_calls.append(seconds)

        class FakeLeagueGameFinder:
            def __init__(self, season_nullable, timeout):
                self.season_nullable = season_nullable
                self.timeout = timeout
                call_number["count"] += 1

            def get_normalized_dict(self):
                raise RuntimeError("permanent failure")

        monkeypatch.setattr(games_module, "LeagueGameFinder", FakeLeagueGameFinder)
        monkeypatch.setattr(games_module.time, "sleep", fake_sleep)

        extractor = games_module.GamesStatsExtractor()
        extractor.retries = 3

        with pytest.raises(RuntimeError, match="permanent failure"):
            extractor.extract("2024-25")

        assert call_number["count"] == 3
        assert sleep_calls == [
            games_module.conf_settings.NBA_API_SLEEP,
            games_module.conf_settings.NBA_API_SLEEP,
        ]

    def test_extract_returns_only_required_columns(self, monkeypatch):
        def fake_sleep(seconds):
            pass

        class FakeLeagueGameFinder:
            def __init__(self, season_nullable, timeout):
                pass

            def get_normalized_dict(self):
                return {
                    "LeagueGameFinderResults": [
                        ["0022400003", 1610612747, "2024-25", "LAL", "Los Angeles Lakers", "2024-10-24", "LAL vs. PHX", "W", 240, 115, 42, 85, 0.494, 11, 29, 0.379, 20, 25, 0.800, 9, 34, 43, 26, 7, 4, 13, 17, 8.0]
                    ]
                }

        monkeypatch.setattr(games_module, "LeagueGameFinder", FakeLeagueGameFinder)
        monkeypatch.setattr(games_module.time, "sleep", fake_sleep)

        extractor = games_module.GamesStatsExtractor()
        result = extractor.extract("2024-25")

        assert list(result.columns) == games_module.GamesStatsExtractor.required_columns

    def test_game_id_team_id_composite_unique(self, monkeypatch):
        def fake_sleep(seconds):
            pass

        class FakeLeagueGameFinder:
            def __init__(self, season_nullable, timeout):
                pass

            def get_normalized_dict(self):
                return {
                    "LeagueGameFinderResults": [
                        ["0022400004", 1610612747, "2024-25", "LAL", "Los Angeles Lakers", "2024-10-25", "LAL vs. GSW", "W", 240, 122, 47, 90, 0.522, 14, 35, 0.400, 14, 18, 0.778, 10, 37, 47, 30, 10, 7, 16, 21, 12.0],
                        ["0022400004", 1610612744, "2024-25", "GSW", "Golden State Warriors", "2024-10-25", "GSW @ LAL", "L", 240, 110, 41, 92, 0.446, 9, 27, 0.333, 19, 24, 0.792, 13, 34, 47, 24, 8, 3, 14, 18, -12.0],
                        ["0022400005", 1610612747, "2024-25", "LAL", "Los Angeles Lakers", "2024-10-26", "LAL vs. LAC", "L", 240, 105, 39, 87, 0.448, 8, 26, 0.308, 19, 25, 0.760, 11, 33, 44, 22, 6, 5, 12, 20, -5.0],
                    ]
                }

        monkeypatch.setattr(games_module, "LeagueGameFinder", FakeLeagueGameFinder)
        monkeypatch.setattr(games_module.time, "sleep", fake_sleep)

        extractor = games_module.GamesStatsExtractor()
        result = extractor.extract("2024-25")

        # Check that GAME_ID + TEAM_ID is unique (composite key)
        composite_key = result["GAME_ID"] + "_" + result["TEAM_ID"].astype(str)
        assert composite_key.is_unique


    @pytest.mark.integration
    def test_extract_hits_real_api(self):
        """Integration test — hits the real NBA API. Requires network access."""
        extractor = games_module.GamesStatsExtractor()
        result = extractor.extract("2024-25")

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "GAME_ID" in result.columns
        assert "TEAM_ID" in result.columns
        # Check composite key uniqueness
        composite_key = result["GAME_ID"] + "_" + result["TEAM_ID"].astype(str)
        assert composite_key.is_unique


    def test_extract_raises_on_invalid_season_format(self):
        extractor = games_module.GamesStatsExtractor()
        with pytest.raises(ValueError, match="Invalid season_id format"):
            extractor.extract("2024")