import pandas as pd
from datetime import datetime
from ingestion.loaders.iceberg_loader import IcebergLoader
from config import settings
from pyiceberg.exceptions import NoSuchTableError
from ingestion.schemas import bookkeeping_schema, bookkeeping_partition_spec


class BookkeepingManager:

    def __init__(self, loader: IcebergLoader):
        """
        Takes an IcebergLoader instance — reuses the same catalog
        connection rather than creating a new one.
        """
        self.loader = loader
        self.table_name = settings.TABLE_BOOKKEEPING

    def initialise(self):
        """
        Creates the bookkeeping table if it doesn't exist.
        """
        table = self.loader.catalog.create_table_if_not_exists(
            self.table_name,
            schema=bookkeeping_schema,
            partition_spec=bookkeeping_partition_spec
        )

    def is_season_complete(self, entity_type: str, season_id: str) -> bool:
        """
        Returns True if this entity_type + season_id combination
        has status = 'complete' in the bookkeeping table.
        """
        try:
            table = self.loader.catalog.load_table(self.table_name)
            df = table.scan().to_pandas()
            
            # Filter for the specific season and entity
            filtered = df[
                (df['season_id'] == season_id) & 
                (df['entity_type'] == entity_type) &
                (df['status'] == 'complete')
            ]
            
            return len(filtered) > 0
        except  NoSuchTableError:
            # Table doesn't exist or other error
            return False

    def mark_in_progress(self, entity_type: str, season_id: str):
        """
        Writes a row with status = 'in_progress' for this
        entity_type + season_id.
        """
        df = pd.DataFrame({
            'season_id': [season_id],
            'entity_type': [entity_type],
            'status': ['in_progress'],
            'rows_loaded': [None],
            'loaded_at': [None]
        })
        
        self.loader.load_bookkeeping_data(df)

    def mark_complete(self, entity_type: str, season_id: str, rows_loaded: int):
        """
        Updates the row to status = 'complete' with rows_loaded count
        and current timestamp.
        """
        df = pd.DataFrame({
            'season_id': [season_id],
            'entity_type': [entity_type],
            'status': ['complete'],
            'rows_loaded': [rows_loaded],
            'loaded_at': [datetime.now()]
        })
        
        self.loader.load_bookkeeping_data(df)