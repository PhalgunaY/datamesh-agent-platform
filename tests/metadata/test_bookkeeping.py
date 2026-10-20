# tests/metadata/test_bookkeeping.py

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from metadata.bookkeeping import BookkeepingManager
from ingestion.loaders.iceberg_loader import IcebergLoader
import metadata.bookkeeping as bookkeeping_module
from pyiceberg.exceptions import NoSuchTableError


class TestBookkeepingManager:

    def _make_manager(self, monkeypatch):
        """Helper to create a BookkeepingManager with mocked loader."""
        monkeypatch.setattr(bookkeeping_module.settings, "ENV", "dev")
        mock_catalog = MagicMock()
        mock_loader = MagicMock(spec=IcebergLoader)
        mock_loader.catalog = mock_catalog
        
        manager = BookkeepingManager(mock_loader)
        return manager, mock_loader, mock_catalog

    def test_init(self, monkeypatch):
        """Test that BookkeepingManager initializes correctly."""
        manager, mock_loader, mock_catalog = self._make_manager(monkeypatch)
        assert manager.loader == mock_loader
        assert manager.table_name == bookkeeping_module.settings.TABLE_BOOKKEEPING

    def test_initialise_creates_table(self, monkeypatch):
        """Test that initialise creates the bookkeeping table."""
        manager, mock_loader, mock_catalog = self._make_manager(monkeypatch)
        mock_table = MagicMock()
        mock_catalog.create_table_if_not_exists.return_value = mock_table
        
        manager.initialise()
        
        mock_catalog.create_table_if_not_exists.assert_called_once_with(
            manager.table_name,
            schema=bookkeeping_module.bookkeeping_schema,
            partition_spec=bookkeeping_module.bookkeeping_partition_spec
        )

    def test_is_season_complete_returns_true_when_complete(self, monkeypatch):
        """Test is_season_complete returns True when status is complete."""
        manager, mock_loader, mock_catalog = self._make_manager(monkeypatch)
        mock_table = MagicMock()
        mock_catalog.load_table.return_value = mock_table
        
        # Mock the scan result
        mock_scan = MagicMock()
        mock_table.scan.return_value = mock_scan
        mock_scan.to_pandas.return_value = pd.DataFrame({
            'season_id': ['2023-24'],
            'entity_type': ['games'],
            'status': ['complete'],
            'rows_loaded': [100],
            'loaded_at': [pd.Timestamp.now()]
        })
        
        result = manager.is_season_complete('games', '2023-24')
        assert result is True

    def test_is_season_complete_returns_false_when_not_complete(self, monkeypatch):
        """Test is_season_complete returns False when status is not complete."""
        manager, mock_loader, mock_catalog = self._make_manager(monkeypatch)
        mock_table = MagicMock()
        mock_catalog.load_table.return_value = mock_table
        
        # Mock the scan result with in_progress status
        mock_scan = MagicMock()
        mock_table.scan.return_value = mock_scan
        mock_scan.to_pandas.return_value = pd.DataFrame({
            'season_id': ['2023-24'],
            'entity_type': ['games'],
            'status': ['in_progress'],
            'rows_loaded': [None],
            'loaded_at': [None]
        })
        
        result = manager.is_season_complete('games', '2023-24')
        assert result is False

    def test_is_season_complete_returns_false_when_no_data(self, monkeypatch):
        """Test is_season_complete returns False when table doesn't exist."""
        manager, mock_loader, mock_catalog = self._make_manager(monkeypatch)
        mock_catalog.load_table.side_effect = NoSuchTableError("Table not found")
        
        result = manager.is_season_complete('games', '2023-24')
        assert result is False

    def test_mark_in_progress_calls_load_data(self, monkeypatch):
        """Test that mark_in_progress calls load_bookkeeping_data with correct data."""
        manager, mock_loader, mock_catalog = self._make_manager(monkeypatch)
        
        manager.mark_in_progress('games', '2023-24')
        
        # Verify load_bookkeeping_data was called
        assert mock_loader.load_bookkeeping_data.called
        args, kwargs = mock_loader.load_bookkeeping_data.call_args
        df = args[0]
        
        assert df['season_id'].iloc[0] == '2023-24'
        assert df['entity_type'].iloc[0] == 'games'
        assert df['status'].iloc[0] == 'in_progress'
        assert pd.isna(df['rows_loaded'].iloc[0])
        assert pd.isna(df['loaded_at'].iloc[0])

    def test_mark_complete_calls_load_data(self, monkeypatch):
        """Test that mark_complete calls load_data with correct data."""
        manager, mock_loader, mock_catalog = self._make_manager(monkeypatch)
        
        manager.mark_complete('games', '2023-24', 150)
        
        # Verify load_bookkeeping_data was called
        assert mock_loader.load_bookkeeping_data.called
        args, kwargs = mock_loader.load_bookkeeping_data.call_args
        df = args[0]
        
        assert df['season_id'].iloc[0] == '2023-24'
        assert df['entity_type'].iloc[0] == 'games'
        assert df['status'].iloc[0] == 'complete'
        assert df['rows_loaded'].iloc[0] == 150
        assert df['loaded_at'].iloc[0] is not None  # Should have timestamp