from pyiceberg.schema import Schema, NestedField
from pyiceberg.types import LongType, StringType, IntegerType, DoubleType, DateType, TimestampType
from pyiceberg.partitioning import PartitionSpec, PartitionField
from pyiceberg.transforms import IdentityTransform

# bronze_teams schema (Dimension, no partition)
bronze_teams_schema = Schema(
    NestedField(1, "TEAM_ID", LongType(), required=True),
    NestedField(2, "FULL_NAME", StringType(), required=True),
    NestedField(3, "ABBREVIATION", StringType(), required=True),
    NestedField(4, "NICKNAME", StringType(), required=True),
    NestedField(5, "CITY", StringType(), required=True),
    NestedField(6, "STATE", StringType(), required=False),
    NestedField(7, "YEAR_FOUNDED", IntegerType(), required=False),
)

bronze_teams_partition_spec = PartitionSpec()  # No partitioning

# bronze_players schema (Dimension, no partition)
bronze_players_schema = Schema(
    NestedField(1, "PERSON_ID", LongType(), required=True),
    NestedField(2, "DISPLAY_LAST_COMMA_FIRST", StringType(), required=True),
    NestedField(3, "DISPLAY_FIRST_LAST", StringType(), required=False),
    NestedField(4, "ROSTERSTATUS", IntegerType(), required=True),
    NestedField(5, "FROM_YEAR", StringType(), required=True),
    NestedField(6, "TO_YEAR", StringType(), required=True),
    NestedField(7, "TEAM_ID", LongType(), required=False),
    NestedField(8, "TEAM_ABBREVIATION", StringType(), required=False),
    NestedField(9, "TEAM_NAME", StringType(), required=False),
    NestedField(10, "GAMES_PLAYED_FLAG", StringType(), required=False),
)

bronze_players_partition_spec = PartitionSpec()  # No partitioning

# bronze_game_stats schema (Fact, partitioned by SEASON_ID)
bronze_game_stats_schema = Schema(
    NestedField(1, "GAME_ID", StringType(), required=True),
    NestedField(2, "TEAM_ID", LongType(), required=True),
    NestedField(3, "SEASON_ID", StringType(), required=True),
    NestedField(4, "TEAM_ABBREVIATION", StringType(), required=True),
    NestedField(5, "TEAM_NAME", StringType(), required=True),
    NestedField(6, "GAME_DATE", StringType(), required=True),
    NestedField(7, "MATCHUP", StringType(), required=True),
    NestedField(8, "WL", StringType(), required=False),
    NestedField(9, "MIN", IntegerType(), required=False),
    NestedField(10, "PTS", IntegerType(), required=False),
    NestedField(11, "FGM", IntegerType(), required=False),
    NestedField(12, "FGA", IntegerType(), required=False),
    NestedField(13, "FG_PCT", DoubleType(), required=False),
    NestedField(14, "FG3M", IntegerType(), required=False),
    NestedField(15, "FG3A", IntegerType(), required=False),
    NestedField(16, "FG3_PCT", DoubleType(), required=False),
    NestedField(17, "FTM", IntegerType(), required=False),
    NestedField(18, "FTA", IntegerType(), required=False),
    NestedField(19, "FT_PCT", DoubleType(), required=False),
    NestedField(20, "OREB", IntegerType(), required=False),
    NestedField(21, "DREB", IntegerType(), required=False),
    NestedField(22, "REB", IntegerType(), required=False),
    NestedField(23, "AST", IntegerType(), required=False),
    NestedField(24, "STL", IntegerType(), required=False),
    NestedField(25, "BLK", IntegerType(), required=False),
    NestedField(26, "TOV", IntegerType(), required=False),
    NestedField(27, "PF", IntegerType(), required=False),
    NestedField(28, "PLUS_MINUS", DoubleType(), required=False),
)

# Partition by SEASON_ID (field_id=3)
bronze_game_stats_partition_spec = PartitionSpec(
    PartitionField(source_id=3, field_id=3, name="SEASON_ID", transform=IdentityTransform())
)

# bronze_player_stats schema (Fact, partitioned by SEASON_ID)
bronze_player_stats_schema = Schema(
    NestedField(1, "PLAYER_ID", LongType(), required=True),
    NestedField(2, "SEASON_ID", StringType(), required=True),
    NestedField(3, "LEAGUE_ID", StringType(), required=False),
    NestedField(4, "TEAM_ID", LongType(), required=False),
    NestedField(5, "TEAM_ABBREVIATION", StringType(), required=False),
    NestedField(6, "PLAYER_AGE", DoubleType(), required=False),
    NestedField(7, "GP", IntegerType(), required=False),
    NestedField(8, "GS", IntegerType(), required=False),
    NestedField(9, "MIN", DoubleType(), required=False),
    NestedField(10, "FGM", DoubleType(), required=False),
    NestedField(11, "FGA", DoubleType(), required=False),
    NestedField(12, "FG_PCT", DoubleType(), required=False),
    NestedField(13, "FG3M", DoubleType(), required=False),
    NestedField(14, "FG3A", DoubleType(), required=False),
    NestedField(15, "FG3_PCT", DoubleType(), required=False),
    NestedField(16, "FTM", DoubleType(), required=False),
    NestedField(17, "FTA", DoubleType(), required=False),
    NestedField(18, "FT_PCT", DoubleType(), required=False),
    NestedField(19, "OREB", DoubleType(), required=False),
    NestedField(20, "DREB", DoubleType(), required=False),
    NestedField(21, "REB", DoubleType(), required=False),
    NestedField(22, "AST", DoubleType(), required=False),
    NestedField(23, "STL", DoubleType(), required=False),
    NestedField(24, "BLK", DoubleType(), required=False),
    NestedField(25, "TOV", DoubleType(), required=False),
    NestedField(26, "PF", DoubleType(), required=False),
    NestedField(27, "PTS", DoubleType(), required=False),
)

# Partition by SEASON_ID (field_id=2)
bronze_player_stats_partition_spec = PartitionSpec(
    PartitionField(source_id=2, field_id=2, name="SEASON_ID", transform=IdentityTransform())
)

# Bookkeeping table schema (no partitioning)
bookkeeping_schema = Schema(
    NestedField(1, "season_id", StringType(), required=True),
    NestedField(2, "entity_type", StringType(), required=True),
    NestedField(3, "status", StringType(), required=True),
    NestedField(4, "rows_loaded", IntegerType(), required=False),
    NestedField(5, "loaded_at", TimestampType(), required=False),
)

bookkeeping_partition_spec = PartitionSpec()  # No partitioning