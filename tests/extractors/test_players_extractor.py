import pytest
import pandas as pd
from types import SimpleNamespace

import ingestion.extractors.players_extractor as players_module


class TestPlayersExtractor:

    def test_init_reads_settings(self, monkeypatch):
        monkeypatch.setattr(players_module.conf_settings, "NBA_API_TIMEOUT", 123)
        monkeypatch.setattr(players_module.conf_settings, "NBA_API_TIMEOUT_RETRIES", 5)

        extractor = players_module.PlayersExtractor()

        assert extractor.timeout == 123
        assert extractor.retries == 5

    def test_extract_returns_dataframe_on_success(self, monkeypatch):
        recorded_sleep = []

        def fake_sleep(seconds):
            recorded_sleep.append(seconds)

        class FakeCommonAllPlayers:
            def __init__(self, is_only_current_season, timeout):
                self.is_only_current_season = is_only_current_season
                self.timeout = timeout

            def get_normalized_dict(self):
                return {
                    "CommonAllPlayers": [
                        [123, "James, LeBron", "LeBron James", "Active", 2003, 2024, 1610612747, "LAL", "LAL", 1],
                        [456, "Durant, Kevin", "Kevin Durant", "Active", 2007, 2024, 1610612751, "BKN", "BKN", 1],
                    ]
                }

        monkeypatch.setattr(players_module, "CommonAllPlayers", FakeCommonAllPlayers)
        monkeypatch.setattr(players_module.time, "sleep", fake_sleep)

        extractor = players_module.PlayersExtractor()
        result = extractor.extract()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert result.iloc[0, 1] == "James, LeBron"
        assert recorded_sleep == [players_module.conf_settings.NBA_API_SLEEP]

    def test_extract_retries_until_success(self, monkeypatch):
        sleep_calls = []
        call_number = {"count": 0}

        def fake_sleep(seconds):
            sleep_calls.append(seconds)

        class FakeCommonAllPlayers:
            def __init__(self, is_only_current_season, timeout):
                self.is_only_current_season = is_only_current_season
                self.timeout = timeout
                call_number["count"] += 1
                self.call_index = call_number["count"]

            def get_normalized_dict(self):
                if self.call_index < 3:
                    raise RuntimeError("temporary failure")
                return {
                    "CommonAllPlayers": [
                        [789, "Player, Test", "Test Player", "Active", 2022, 2024, 1610612752, "NOP", "NOP", 1]
                    ]
                }

        monkeypatch.setattr(players_module, "CommonAllPlayers", FakeCommonAllPlayers)
        monkeypatch.setattr(players_module.time, "sleep", fake_sleep)

        extractor = players_module.PlayersExtractor()
        extractor.retries = 3

        result = extractor.extract()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert call_number["count"] == 3
        assert sleep_calls == [
            players_module.conf_settings.NBA_API_SLEEP,
            players_module.conf_settings.NBA_API_SLEEP,
            players_module.conf_settings.NBA_API_SLEEP,
        ]

    def test_extract_raises_after_max_retries(self, monkeypatch):
        sleep_calls = []
        call_number = {"count": 0}

        def fake_sleep(seconds):
            sleep_calls.append(seconds)

        class FakeCommonAllPlayers:
            def __init__(self, is_only_current_season, timeout):
                self.is_only_current_season = is_only_current_season
                self.timeout = timeout
                call_number["count"] += 1

            def get_normalized_dict(self):
                raise RuntimeError("permanent failure")

        monkeypatch.setattr(players_module, "CommonAllPlayers", FakeCommonAllPlayers)
        monkeypatch.setattr(players_module.time, "sleep", fake_sleep)

        extractor = players_module.PlayersExtractor()
        extractor.retries = 3

        with pytest.raises(RuntimeError, match="permanent failure"):
            extractor.extract()

        assert call_number["count"] == 3
        assert sleep_calls == [
            players_module.conf_settings.NBA_API_SLEEP,
            players_module.conf_settings.NBA_API_SLEEP,
        ]

    def test_extract_returns_only_required_columns(self, monkeypatch):
        def fake_sleep(seconds):
            pass

        class FakeCommonAllPlayers:
            def __init__(self, is_only_current_season, timeout):
                pass

            def get_normalized_dict(self):
                return {
                    "CommonAllPlayers": [
                        [123, "Doe, John", "John Doe", "Active", 2020, 2024, 1, "LAL", "LAL", 1]
                    ]
                }

        monkeypatch.setattr(players_module, "CommonAllPlayers", FakeCommonAllPlayers)
        monkeypatch.setattr(players_module.time, "sleep", fake_sleep)

        extractor = players_module.PlayersExtractor()
        result = extractor.extract()

        assert list(result.columns) == players_module.PlayersExtractor.required_columns

    def test_person_id_is_unique(self, monkeypatch):
        def fake_sleep(seconds):
            pass

        class FakeCommonAllPlayers:
            def __init__(self, is_only_current_season, timeout):
                pass

            def get_normalized_dict(self):
                return {
                    "CommonAllPlayers": [
                        [123, "Doe, John", "John Doe", "Active", 2020, 2024, 1, "LAL", "LAL", 1],
                        [456, "Smith, Jane", "Jane Smith", "Active", 2021, 2024, 2, "BOS", "BOS", 1],
                        [789, "Brown, Sam", "Sam Brown", "Active", 2022, 2024, 3, "MIA", "MIA", 1],
                    ]
                }

        monkeypatch.setattr(players_module, "CommonAllPlayers", FakeCommonAllPlayers)
        monkeypatch.setattr(players_module.time, "sleep", fake_sleep)

        extractor = players_module.PlayersExtractor()
        result = extractor.extract()

        assert result["PERSON_ID"].is_unique


    @pytest.mark.integration
    def test_extract_hits_real_api(self):
        """Integration test — hits the real NBA API. Requires network access."""
        extractor = players_module.PlayersExtractor()
        result = extractor.extract()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "PERSON_ID" in result.columns
        assert result["PERSON_ID"].is_unique
