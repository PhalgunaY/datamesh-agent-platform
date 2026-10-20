import os
import boto3
import pandas as pd
import pyarrow as pa
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.catalog.glue import GlueCatalog
from pyiceberg.schema import Schema
from pyiceberg.partitioning import PartitionSpec
from pyiceberg.exceptions import NamespaceAlreadyExistsError

from config import settings
from ingestion.schemas import (
    bronze_teams_schema,
    bronze_teams_partition_spec,
    bronze_players_schema,
    bronze_players_partition_spec,
    bronze_game_stats_schema,
    bronze_game_stats_partition_spec,
    bronze_player_stats_schema,
    bronze_player_stats_partition_spec,
    bookkeeping_schema,
    bookkeeping_partition_spec
)


class IcebergLoader:
    def __init__(self):
        self.env = settings.ENV
        self.catalog = self._create_catalog()
        self._ensure_namespace()
        self.schemas = {
            settings.TABLE_TEAMS: bronze_teams_schema,
            settings.TABLE_PLAYERS: bronze_players_schema,
            settings.TABLE_GAME_STATS: bronze_game_stats_schema,
            settings.TABLE_PLAYER_STATS: bronze_player_stats_schema,
        }
        self.partition_specs = {
            settings.TABLE_TEAMS: bronze_teams_partition_spec,
            settings.TABLE_PLAYERS: bronze_players_partition_spec,
            settings.TABLE_GAME_STATS: bronze_game_stats_partition_spec,
            settings.TABLE_PLAYER_STATS: bronze_player_stats_partition_spec,
        }

    def _ensure_namespace(self):
        try:
            self.catalog.create_namespace(settings.BRONZE_NAMESPACE)
        except NamespaceAlreadyExistsError:
            pass

    def _create_catalog(self):
        if self.env == 'dev':
            # Ensure local paths exist
            catalog_path = settings.LOCAL_CATALOG_PATH
            warehouse_path = settings.LOCAL_BRONZE_PATH
            
            # For local development, use the path directly (PyIceberg can handle local paths)
            os.makedirs(warehouse_path, exist_ok=True)
            os.makedirs(catalog_path, exist_ok=True)
            
            return SqlCatalog(
                "local",
                **{
                    "type": "sqlite",
                    "uri": f"sqlite:///{catalog_path}/catalog.db",
                    "warehouse": warehouse_path
                }
            )
        elif self.env == 'prod':
            glue_client = boto3.client(
                "glue",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            return GlueCatalog(
                "glue",
                client=glue_client,
                **{
                    "warehouse": f"s3://{settings.AWS_BRONZE_BUCKET}/",
                }
            )
        else:
            raise ValueError(f"Unsupported environment: {self.env}")

    def load_data(self, table_name: str, df: pd.DataFrame):
        """
        Load data into Iceberg table via upsert.

        Args:
            table_name: Name of the table (e.g., 'bronze.teams')
            df: Pandas DataFrame to load
        """
        # Get schema and partition spec
        schema = self.schemas[table_name]
        partition_spec = self.partition_specs[table_name]

        # Create table if not exists
        table = self.catalog.create_table_if_not_exists(
            table_name,
            schema=schema,
            partition_spec=partition_spec
        )

        # Convert DataFrame to PyArrow table
        pa_table = pa.Table.from_pandas(df, preserve_index=False)
        target_schema = schema.as_arrow()
        expected_cols = [field.name for field in target_schema]
        actual_cols = list(pa_table.column_names)

        if set(actual_cols) != set(expected_cols):
            raise ValueError(
                f"DataFrame columns do not match schema columns. "
                f"expected={expected_cols}, actual={actual_cols}"
            )

        if actual_cols != expected_cols:
            pa_table = pa_table.select(expected_cols)

        pa_table = pa_table.cast(target_schema)

        # Get merge keys
        merge_keys = settings.MERGE_KEYS[table_name]

        # Upsert data
        table.upsert(pa_table, join_cols=merge_keys)

    def load_bookkeeping_data(self, df: pd.DataFrame):
        """
        Load bookkeeping data into the bookkeeping table.
        This method handles the bookkeeping table specifically since it's not
        in the main schemas dictionary.

        Args:
            df: Pandas DataFrame with bookkeeping data
        """
        
        table_name = settings.TABLE_BOOKKEEPING
        
        # Create table if not exists
        table = self.catalog.create_table_if_not_exists(
            table_name,
            schema=bookkeeping_schema,
            partition_spec=bookkeeping_partition_spec
        )

        # Convert DataFrame to PyArrow table
        pa_table = pa.Table.from_pandas(df, preserve_index=False)
        target_schema = bookkeeping_schema.as_arrow()
        expected_cols = [field.name for field in target_schema]
        actual_cols = list(pa_table.column_names)

        if set(actual_cols) != set(expected_cols):
            raise ValueError(
                f"Bookkeeping DataFrame columns do not match schema columns. "
                f"expected={expected_cols}, actual={actual_cols}"
            )

        if actual_cols != expected_cols:
            pa_table = pa_table.select(expected_cols)

        pa_table = pa_table.cast(target_schema)

        # Get merge keys for bookkeeping
        merge_keys = settings.MERGE_KEYS[table_name]

        # Upsert data
        table.upsert(pa_table, join_cols=merge_keys)
