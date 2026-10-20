# tests/loaders/test_iceberg_loader.py

import os
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, call
import ingestion.loaders.iceberg_loader as loader_module
from ingestion.loaders.iceberg_loader import IcebergLoader


class TestIcebergLoaderInit:

    def test_raises_on_invalid_environment(self, monkeypatch):
        """
        If ENV is set to something other than dev/prod,
        the loader should raise ValueError on init.
        Hint: monkeypatch settings.ENV to "staging"
        """
        monkeypatch.setattr(loader_module.settings, "ENV", "staging")
        with pytest.raises(ValueError, match="Unsupported environment: staging"):
            IcebergLoader()

    def test_dev_creates_sql_catalog(self, monkeypatch):
        """
        When ENV=dev, _create_catalog should return a SqlCatalog.
        Hint: patch SqlCatalog and _ensure_namespace to isolate
        """
        monkeypatch.setattr(loader_module.settings, "ENV", "dev")
        monkeypatch.setattr(loader_module.settings, "LOCAL_CATALOG_PATH", "/tmp/catalog")
        monkeypatch.setattr(loader_module.settings, "LOCAL_BRONZE_PATH", "/tmp/warehouse")
        
        with patch("ingestion.loaders.iceberg_loader.SqlCatalog") as mock_sql_catalog, \
             patch.object(IcebergLoader, "_ensure_namespace"):
            loader = IcebergLoader()
            mock_sql_catalog.assert_called_once()
            assert isinstance(loader.catalog, MagicMock)  # Since it's patched

    def test_prod_creates_glue_catalog(self, monkeypatch):
        """
        When ENV=prod, _create_catalog should return a GlueCatalog.
        Hint: patch GlueCatalog and _ensure_namespace
        """
        monkeypatch.setattr(loader_module.settings, "ENV", "prod")
        monkeypatch.setattr(loader_module.settings, "AWS_BRONZE_BUCKET", "test-bucket")
        monkeypatch.setattr(loader_module.settings, "AWS_REGION", "us-east-1")
        
        with patch("ingestion.loaders.iceberg_loader.GlueCatalog") as mock_glue_catalog, \
             patch.object(IcebergLoader, "_ensure_namespace"):
            loader = IcebergLoader()
            mock_glue_catalog.assert_called_once()
            assert isinstance(loader.catalog, MagicMock)  # Since it's patched


class TestIcebergLoaderLoadData:

    def _make_loader(self, monkeypatch):
        """
        Helper that builds a loader with a fully mocked catalog.
        Use this in every test in this class.
        """
        monkeypatch.setattr(loader_module.settings, "ENV", "dev")
        mock_catalog = MagicMock()
        mock_catalog.create_namespace.side_effect = None
        
        with patch.object(IcebergLoader, "_create_catalog", return_value=mock_catalog):
            loader = IcebergLoader()
        return loader, mock_catalog

    def test_load_data_creates_table_if_not_exists(self, monkeypatch):
        """
        load_data should call create_table_if_not_exists with the
        correct table name, schema, and partition spec.
        """
        loader, mock_catalog = self._make_loader(monkeypatch)
        mock_table = MagicMock()
        mock_catalog.create_table_if_not_exists.return_value = mock_table
        
        df = pd.DataFrame({
            "TEAM_ID": [1], 
            "FULL_NAME": ["Test Team"],
            "ABBREVIATION": ["TST"],
            "NICKNAME": ["Test"],
            "CITY": ["Test City"],
            "STATE": [None],
            "YEAR_FOUNDED": [None]
        })
        loader.load_data(loader_module.settings.TABLE_TEAMS, df)
        
        mock_catalog.create_table_if_not_exists.assert_called_once_with(
            loader_module.settings.TABLE_TEAMS,
            schema=loader.schemas[loader_module.settings.TABLE_TEAMS],
            partition_spec=loader.partition_specs[loader_module.settings.TABLE_TEAMS]
        )

    def test_load_data_calls_upsert_with_correct_merge_keys(self, monkeypatch):
        """
        load_data should call table.upsert with the merge keys
        defined in settings.MERGE_KEYS for that table.
        Verify join_cols matches settings.MERGE_KEYS[table_name].
        """
        loader, mock_catalog = self._make_loader(monkeypatch)
        mock_table = MagicMock()
        mock_catalog.create_table_if_not_exists.return_value = mock_table
        
        df = pd.DataFrame({
            "TEAM_ID": [1], 
            "FULL_NAME": ["Test Team"],
            "ABBREVIATION": ["TST"],
            "NICKNAME": ["Test"],
            "CITY": ["Test City"],
            "STATE": [None],
            "YEAR_FOUNDED": [None]
        })
        loader.load_data(loader_module.settings.TABLE_TEAMS, df)
        
        expected_merge_keys = loader_module.settings.MERGE_KEYS[loader_module.settings.TABLE_TEAMS]
        mock_table.upsert.assert_called_once()
        args, kwargs = mock_table.upsert.call_args
        assert kwargs["join_cols"] == expected_merge_keys

    def test_load_data_raises_on_unknown_table(self, monkeypatch):
        """
        If table_name is not in self.schemas, load_data should raise KeyError.
        """
        loader, mock_catalog = self._make_loader(monkeypatch)
        
        df = pd.DataFrame({"TEAM_ID": [1], "FULL_NAME": ["Test Team"]})
        with pytest.raises(KeyError):
            loader.load_data("unknown.table", df)

    def test_load_data_converts_dataframe_to_arrow(self, monkeypatch):
        """
        Verify that load_data converts the DataFrame to a PyArrow table
        before calling upsert. Check that upsert receives a pyarrow.Table
        not a pandas DataFrame.
        """
        loader, mock_catalog = self._make_loader(monkeypatch)
        mock_table = MagicMock()
        mock_catalog.create_table_if_not_exists.return_value = mock_table
        
        df = pd.DataFrame({
            "TEAM_ID": [1], 
            "FULL_NAME": ["Test Team"],
            "ABBREVIATION": ["TST"],
            "NICKNAME": ["Test"],
            "CITY": ["Test City"],
            "STATE": [None],
            "YEAR_FOUNDED": [None]
        })
        loader.load_data(loader_module.settings.TABLE_TEAMS, df)
        
        mock_table.upsert.assert_called_once()
        args, kwargs = mock_table.upsert.call_args
        pa_table = args[0]  # First positional argument
        import pyarrow as pa
        assert isinstance(pa_table, pa.Table)


class TestIcebergLoaderIntegration:

    @pytest.mark.integration
    @pytest.mark.skipif(os.name == 'nt', reason="PyIceberg has Windows path parsing issues in integration tests")
    def test_load_and_read_teams(self, tmp_path):
        """
        Integration test using a real SqlCatalog in a temp directory.
        Write dummy teams data, read it back, verify row count and values.
        Hint: use tmp_path pytest fixture for a clean temp directory,
        monkeypatch settings to point at tmp_path
        """
        # Set up temporary paths
        catalog_path = tmp_path / "catalog"
        warehouse_path = tmp_path / "warehouse"
        
        with patch.object(loader_module.settings, "ENV", "dev"), \
             patch.object(loader_module.settings, "LOCAL_CATALOG_PATH", str(catalog_path)), \
             patch.object(loader_module.settings, "LOCAL_BRONZE_PATH", str(warehouse_path)):
            
            loader = IcebergLoader()
            
            # Create dummy teams data
            teams_df = pd.DataFrame({
                "TEAM_ID": [1610612737, 1610612738],
                "FULL_NAME": ["Atlanta Hawks", "Boston Celtics"],
                "ABBREVIATION": ["ATL", "BOS"],
                "CITY": ["Atlanta", "Boston"],
                "NICKNAME": ["Hawks", "Celtics"],
                "STATE": [None, "MA"],
                "YEAR_FOUNDED": [1949, 1946]
            })
            
            # Load the data
            loader.load_data(loader_module.settings.TABLE_TEAMS, teams_df)
            
            # Read it back
            table = loader.catalog.load_table(loader_module.settings.TABLE_TEAMS)
            result_df = table.scan().to_pandas()
            
            # Verify
            assert len(result_df) == 2
            result_sorted = result_df.sort_values("TEAM_ID").reset_index(drop=True)
            assert result_sorted["TEAM_ID"].tolist() == [1610612737, 1610612738]
            assert result_sorted["FULL_NAME"].tolist() == ["Atlanta Hawks", "Boston Celtics"]