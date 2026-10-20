import pytest
import pandas as pd

import ingestion.extractors.players_stats_extractor as players_stats_module


class TestPlayersStatsExtractor:

    def test_init_reads_settings(self, monkeypatch):
        monkeypatch.setattr(players_stats_module.conf_settings, "NBA_API_TIMEOUT", 123)
        monkeypatch.setattr(players_stats_module.conf_settings, "NBA_API_TIMEOUT_RETRIES", 5)

        extractor = players_stats_module.PlayersStatsExtractor()

        assert extractor.timeout == 123
        assert extractor.retries == 5

    def test_extract_returns_dataframe_on_success(self, monkeypatch):
        recorded_sleep = []

        def fake_sleep(seconds):
            recorded_sleep.append(seconds)

        class FakePlayerCareerStats:
            def __init__(self, player_id, timeout):
                self.player_id = player_id
                self.timeout = timeout

            def get_normalized_dict(self):
                return {
                    "SeasonTotalsRegularSeason": [
                        [2544, "2024-25", "00", 1610612747, "LAL", 35.4, 82, 82, 35.4, 9.3, 19.9, 0.469, 2.5, 6.8, 0.369, 5.1, 6.7, 0.759, 1.1, 5.3, 6.4, 7.1, 1.1, 0.6, 2.1, 1.9, 27.4],
                    ]
                }

        monkeypatch.setattr(players_stats_module, "PlayerCareerStats", FakePlayerCareerStats)
        monkeypatch.setattr(players_stats_module.time, "sleep", fake_sleep)

        extractor = players_stats_module.PlayersStatsExtractor()
        result = extractor.extract(2544)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["PLAYER_ID"] == 2544
        assert recorded_sleep == [players_stats_module.conf_settings.NBA_API_SLEEP]

    def test_extract_filters_by_season_id(self, monkeypatch):
        def fake_sleep(seconds):
            pass

        class FakePlayerCareerStats:
            def __init__(self, player_id, timeout):
                pass

            def get_normalized_dict(self):
                return {
                    "SeasonTotalsRegularSeason": [
                        [2544, "2023-24", "00", 1610612747, "LAL", 35.4, 82, 82, 35.4, 9.3, 19.9, 0.469, 2.5, 6.8, 0.369, 5.1, 6.7, 0.759, 1.1, 5.3, 6.4, 7.1, 1.1, 0.6, 2.1, 1.9, 27.4],
                        [2544, "2024-25", "00", 1610612747, "LAL", 36.1, 82, 82, 36.1, 10.0, 21.0, 0.476, 3.0, 7.0, 0.429, 5.2, 7.2, 0.722, 1.2, 5.4, 6.6, 7.4, 1.2, 0.7, 2.3, 2.0, 28.7],
                    ]
                }

        monkeypatch.setattr(players_stats_module, "PlayerCareerStats", FakePlayerCareerStats)
        monkeypatch.setattr(players_stats_module.time, "sleep", fake_sleep)

        extractor = players_stats_module.PlayersStatsExtractor()
        result = extractor.extract(2544, season_id="2024-25")

        assert len(result) == 1
        assert result.iloc[0]["SEASON_ID"] == "2024-25"

    def test_extract_retries_until_success(self, monkeypatch):
        sleep_calls = []
        call_number = {"count": 0}

        def fake_sleep(seconds):
            sleep_calls.append(seconds)

        class FakePlayerCareerStats:
            def __init__(self, player_id, timeout):
                call_number["count"] += 1
                self.player_id = player_id
                self.timeout = timeout
                self.call_index = call_number["count"]

            def get_normalized_dict(self):
                if self.call_index < 3:
                    raise RuntimeError("temporary failure")
                return {
                    "SeasonTotalsRegularSeason": [
                        [101, "2024-25", "00", 1610612747, "LAL", 35.4, 82, 82, 35.4, 9.3, 19.9, 0.469, 2.5, 6.8, 0.369, 5.1, 6.7, 0.759, 1.1, 5.3, 6.4, 7.1, 1.1, 0.6, 2.1, 1.9, 27.4],
                    ]
                }

        monkeypatch.setattr(players_stats_module, "PlayerCareerStats", FakePlayerCareerStats)
        monkeypatch.setattr(players_stats_module.time, "sleep", fake_sleep)

        extractor = players_stats_module.PlayersStatsExtractor()
        extractor.retries = 3

        result = extractor.extract(101)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert call_number["count"] == 3
        assert sleep_calls == [
            players_stats_module.conf_settings.NBA_API_SLEEP,
            players_stats_module.conf_settings.NBA_API_SLEEP,
            players_stats_module.conf_settings.NBA_API_SLEEP,
        ]

    def test_extract_raises_after_max_retries(self, monkeypatch):
        sleep_calls = []
        call_number = {"count": 0}

        def fake_sleep(seconds):
            sleep_calls.append(seconds)

        class FakePlayerCareerStats:
            def __init__(self, player_id, timeout):
                call_number["count"] += 1
                self.player_id = player_id
                self.timeout = timeout

            def get_normalized_dict(self):
                raise RuntimeError("permanent failure")

        monkeypatch.setattr(players_stats_module, "PlayerCareerStats", FakePlayerCareerStats)
        monkeypatch.setattr(players_stats_module.time, "sleep", fake_sleep)

        extractor = players_stats_module.PlayersStatsExtractor()
        extractor.retries = 3

        with pytest.raises(RuntimeError, match="permanent failure"):
            extractor.extract(101)

        assert call_number["count"] == 3
        assert sleep_calls == [
            players_stats_module.conf_settings.NBA_API_SLEEP,
            players_stats_module.conf_settings.NBA_API_SLEEP,
        ]

    def test_extract_returns_empty_df_on_missing_stats(self, monkeypatch):
        """Players with no career stats return empty DataFrame, not an exception."""
        def fake_sleep(seconds):
            pass

        class FakePlayerCareerStats:
            def __init__(self, player_id, timeout):
                pass

            def get_normalized_dict(self):
                raise KeyError("resultSet")

        monkeypatch.setattr(
            players_stats_module, "PlayerCareerStats", FakePlayerCareerStats
        )
        monkeypatch.setattr(players_stats_module.time, "sleep", fake_sleep)

        extractor = players_stats_module.PlayersStatsExtractor()
        result = extractor.extract(1629152)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        assert list(result.columns) == players_stats_module.PlayersStatsExtractor.required_columns
    
    def test_extract_returns_only_required_columns(self, monkeypatch):
        def fake_sleep(seconds):
            pass

        class FakePlayerCareerStats:
            def __init__(self, player_id, timeout):
                pass

            def get_normalized_dict(self):
                return {
                    "SeasonTotalsRegularSeason": [
                        [101, "2024-25", "00", 1610612747, "LAL", 35.4, 82, 82, 35.4, 9.3, 19.9, 0.469, 2.5, 6.8, 0.369, 5.1, 6.7, 0.759, 1.1, 5.3, 6.4, 7.1, 1.1, 0.6, 2.1, 1.9, 27.4],
                    ]
                }

        monkeypatch.setattr(players_stats_module, "PlayerCareerStats", FakePlayerCareerStats)
        monkeypatch.setattr(players_stats_module.time, "sleep", fake_sleep)

        extractor = players_stats_module.PlayersStatsExtractor()
        result = extractor.extract(101)

        assert list(result.columns) == players_stats_module.PlayersStatsExtractor.required_columns

    @pytest.mark.integration
    def test_extract_hits_real_api(self, monkeypatch):
        """Integration test — hits the real NBA API. Requires network access."""
        extractor = players_stats_module.PlayersStatsExtractor()
        result = extractor.extract(101)

        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 0
        assert "PLAYER_ID" in result.columns
        assert "SEASON_ID" in result.columns


    def test_extract_raises_on_invalid_season_format(self):
        extractor = players_stats_module.PlayersStatsExtractor()
        with pytest.raises(ValueError, match="Invalid season_id format"):
            extractor.extract(2544, season_id="2024")
