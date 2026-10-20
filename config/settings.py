import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# --Environment-----------------------------------------
ENV = os.getenv('ENV', 'dev')

# --Storage Paths-----------------------------------------
LOCAL_BRONZE_PATH = os.getenv('LOCAL_BRONZE_PATH', './data/bronze')
LOCAL_CATALOG_PATH = os.getenv('LOCAL_CATALOG_PATH', './data/catalog')


AWS_BRONZE_BUCKET = os.getenv('AWS_BRONZE_BUCKET', os.getenv('S3_BUCKET_NAME'))
AWS_GLUE_DATABASE = os.getenv('AWS_GLUE_DATABASE')
AWS_REGION = os.getenv('AWS_REGION', "us-east-2")
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_SESSION_TOKEN = os.getenv('AWS_SESSION_TOKEN')


# --Season Configuration-----------------------------------------
SEASON_START_YEAR = 2004
SEASON_END_YEAR = 2024

SEASONS = [f"{year}-{str(year + 1)[-2:]}" for year in range(SEASON_START_YEAR, SEASON_END_YEAR + 1)]

# --Table Names-----------------------------------------
BRONZE_NAMESPACE= "bronze"

TABLE_TEAMS = f"{BRONZE_NAMESPACE}.teams"
TABLE_PLAYERS = f"{BRONZE_NAMESPACE}.players"
TABLE_GAME_STATS = f"{BRONZE_NAMESPACE}.game_stats"
TABLE_PLAYER_STATS = f"{BRONZE_NAMESPACE}.player_stats"
TABLE_BOOKKEEPING = f"{BRONZE_NAMESPACE}.pipeline_bookkeeping"

# --Merge Keys per table-----------------------------------------
MERGE_KEYS = {
    TABLE_TEAMS: ["TEAM_ID"],
    TABLE_PLAYERS: ["PERSON_ID"],
    TABLE_GAME_STATS: ["GAME_ID", "TEAM_ID"],
    TABLE_PLAYER_STATS: ["PLAYER_ID", "SEASON_ID", "TEAM_ID"],
    TABLE_BOOKKEEPING: ["season_id", "entity_type"],
}


# --NBA API Configuration-----------------------------------------
NBA_API_TIMEOUT = 60  # increase from 30 to 60 seconds  # seconds per request
NBA_API_TIMEOUT_RETRIES = 3  # number of retries for failed requests
NBA_API_SLEEP = 1  # seconds to sleep between requests to avoid rate limits