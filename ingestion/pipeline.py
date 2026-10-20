# pipeline.py
import time
import logging
import os
from datetime import datetime

os.makedirs("logs", exist_ok=True)
log_filename = f"logs/pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Get the root logger and configure it explicitly
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove any existing handlers
root_logger.handlers.clear()

# Add console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Add file handler
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Shared formatter
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(name)s — %(message)s"
)
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)



from ingestion.extractors.teams_extractor import TeamsExtractor
from ingestion.extractors.players_extractor import PlayersExtractor
from ingestion.extractors.games_extractor import GamesStatsExtractor
from ingestion.extractors.players_stats_extractor import PlayersStatsExtractor
from ingestion.loaders.iceberg_loader import IcebergLoader
from metadata.bookkeeping import BookkeepingManager
from config import settings
import logging
from pyiceberg.exceptions import NoSuchTableError


def run_pipeline():
    try:
        # Initialise
        loader = IcebergLoader()
        bookkeeping = BookkeepingManager(loader)
        bookkeeping.initialise()

        # Step 1 — Teams (static, no bookkeeping needed)
        logger.info("Ingesting bronze_teams")
        teams_df = TeamsExtractor().extract()
        loader.load_data(settings.TABLE_TEAMS, teams_df)

        # Step 2 — Players (single call, no bookkeeping needed)
        logger.info("Ingesting bronze_players")
        players_df = PlayersExtractor().extract()
        loader.load_data(settings.TABLE_PLAYERS, players_df)

        # Step 3 — Game stats (season by season)
        extractor = GamesStatsExtractor()
        for season_id in settings.SEASONS:
            if bookkeeping.is_season_complete("game_stats", season_id):
                logger.info(f"Skipping game_stats {season_id} — already complete")
                continue
            bookkeeping.mark_in_progress("game_stats", season_id)
            df = extractor.extract(season_id)

            # Add temporarily to pipeline.py after extracting the df
            # Check for duplicates on merge key
            dupes = df[df.duplicated(subset=["GAME_ID", "TEAM_ID"], keep=False)]
            print(f"Duplicate rows in {season_id}: {len(dupes)}")
            print(dupes.sort_values(["GAME_ID", "TEAM_ID"]).head(10).to_string())


            loader.load_data(settings.TABLE_GAME_STATS, df)
            bookkeeping.mark_complete("game_stats", season_id, len(df))
            logger.info(f"Completed game_stats {season_id} — {len(df)} rows")

        # Step 4 — Player stats (one call per player, all seasons)
        player_ids = loader.catalog.load_table(settings.TABLE_PLAYERS) \
                                .scan().to_pandas()["PERSON_ID"].tolist()
        
        # Resumability via Bronze table check — no season-level bookkeeping needed
        logger.info("Ingesting bronze_player_stats")
        extractor = PlayersStatsExtractor()
        total_rows = 0

        try:
            existing = set(
                loader.catalog.load_table(settings.TABLE_PLAYER_STATS)
                            .scan().to_pandas()["PLAYER_ID"].unique().tolist()
            )
        except NoSuchTableError:
            existing = set()

        for i, player_id in enumerate(player_ids):
            if player_id in existing:
                logger.info(f"Skipping player {player_id} — already loaded")
                continue
            
            # Cooldown every 50 players to avoid rate limiting
            if i > 0 and i % 50 == 0:
                logger.info(f"Processed {i} players — cooling down 60 seconds")
                time.sleep(60)
            
            df = extractor.extract(player_id)
            if not df.empty:
                loader.load_data(settings.TABLE_PLAYER_STATS, df)
                total_rows += len(df)

        logger.info(f"Completed player_stats — {total_rows} rows loaded")

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    run_pipeline()