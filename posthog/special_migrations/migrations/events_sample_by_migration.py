from constance import config

from ee.clickhouse.client import sync_execute
from ee.clickhouse.sql.events import EVENTS_TABLE, EVENTS_TABLE_MV_SQL, EVENTS_TABLE_SQL
from posthog.constants import AnalyticsDBMS
from posthog.settings import CLICKHOUSE_CLUSTER, CLICKHOUSE_DATABASE
from posthog.special_migrations.definition import SpecialMigrationDefinition, SpecialMigrationOperation
from posthog.version_requirement import ServiceVersionRequirement

ONE_DAY = 60 * 60 * 24

TEMPORARY_TABLE_NAME = "temp_events"


class Migration(SpecialMigrationDefinition):

    description = "Events table migration for compatible sample by column."

    posthog_min_version = "1.30.0"
    posthog_max_version = "1.31.0"

    service_version_requirements = [
        ServiceVersionRequirement(service="clickhouse", supported_version=">=21.6.0,<21.7.0"),
    ]

    operations = [
        SpecialMigrationOperation(
            database=AnalyticsDBMS.CLICKHOUSE,
            sql=f"CREATE TABLE IF NOT EXISTS {TEMPORARY_TABLE_NAME} AS {EVENTS_TABLE} ON CLUSTER {CLICKHOUSE_CLUSTER}",
            rollback=f"DROP TABLE IF EXISTS {TEMPORARY_TABLE_NAME} ON CLUSTER {CLICKHOUSE_CLUSTER}",
        ),
        SpecialMigrationOperation(
            database=AnalyticsDBMS.CLICKHOUSE,
            sql=f"""
            INSERT INTO {TEMPORARY_TABLE_NAME}
            SELECT * 
            FROM {EVENTS_TABLE}
            WHERE timestamp < toYYYYMM(now()) - 1
            AND timestamp >= (SELECT max(timestamp) FROM {TEMPORARY_TABLE_NAME}""",
            rollback=f"TRUNCATE TABLE {TEMPORARY_TABLE_NAME} ON CLUSTER {CLICKHOUSE_CLUSTER}",
        ),
        SpecialMigrationOperation(
            database=AnalyticsDBMS.CLICKHOUSE,
            sql=f"DETACH TABLE {EVENTS_TABLE_MV_SQL} ON CLUSTER {CLICKHOUSE_CLUSTER}",
            rollback=f"ATTACH TABLE {EVENTS_TABLE_MV_SQL} ON CLUSTER {CLICKHOUSE_CLUSTER}",
            side_effect=lambda: setattr(config, "MATERIALIZED_COLUMNS_ENABLED", False),
            side_effect_rollback=lambda: setattr(config, "MATERIALIZED_COLUMNS_ENABLED", True),
        ),
        SpecialMigrationOperation(
            database=AnalyticsDBMS.CLICKHOUSE,
            sql=f"""
            INSERT INTO {TEMPORARY_TABLE_NAME}
            SELECT * 
            FROM {EVENTS_TABLE}
            WHERE timestamp >= toYYYYMM(now()) - 1
            AND timestamp >= (SELECT max(timestamp) FROM {TEMPORARY_TABLE_NAME}""",
            rollback=f"TRUNCATE TABLE {TEMPORARY_TABLE_NAME} ON CLUSTER {CLICKHOUSE_CLUSTER}",
        ),
        SpecialMigrationOperation(
            database=AnalyticsDBMS.CLICKHOUSE,
            sql=f"""
                RENAME TABLE
                    {CLICKHOUSE_DATABASE}.{EVENTS_TABLE} to {CLICKHOUSE_DATABASE}.{EVENTS_TABLE}_old,
                    {CLICKHOUSE_DATABASE}.{TEMPORARY_TABLE_NAME} to {CLICKHOUSE_DATABASE}.{EVENTS_TABLE},
                ON CLUSTER {CLICKHOUSE_CLUSTER}
            """,
            rollback=f"""
                RENAME TABLE
                    {CLICKHOUSE_DATABASE}.{EVENTS_TABLE} to {CLICKHOUSE_DATABASE}.{EVENTS_TABLE}_failed,
                    {CLICKHOUSE_DATABASE}.{EVENTS_TABLE}_old to {CLICKHOUSE_DATABASE}.{EVENTS_TABLE},
                ON CLUSTER {CLICKHOUSE_CLUSTER}
            """,
        ),
        SpecialMigrationOperation(
            database=AnalyticsDBMS.CLICKHOUSE,
            sql=f"ATTACH TABLE {EVENTS_TABLE_MV_SQL} ON CLUSTER {CLICKHOUSE_CLUSTER}",
            rollback=f"DETACH TABLE {EVENTS_TABLE_MV_SQL} ON CLUSTER {CLICKHOUSE_CLUSTER}",
            side_effect=lambda: setattr(config, "MATERIALIZED_COLUMNS_ENABLED", True),
            side_effect_rollback=lambda: setattr(config, "MATERIALIZED_COLUMNS_ENABLED", False),
        ),
    ]

    def is_required(self):
        res = sync_execute(f"SHOW CREATE TABLE {EVENTS_TABLE}")
        return "SAMPLE BY uuid" in res[0][0]

    def healthcheck(self):
        result = sync_execute(
            """
        SELECT (free_space.size / event_table_size.size) FROM 
            (SELECT 1 as jc, 'event_table_size', sum(bytes) as size FROM system.parts WHERE table = 'sharded_events') event_table_size
        JOIN 
            (SELECT 1 as jc, 'free_disk_space', free_space as size FROM system.disks WHERE name = 'default') free_space
        ON event_table_size.jc=free_space.jc 
        """
        )
        event_size_to_free_space_ratio = result[0][0]
        # Require 1.5x the events table in free space to be available
        if event_size_to_free_space_ratio < 1.5:
            return (True, None)
        else:
            result = sync_execute(
                """
            SELECT formatReadableSize(free_space.size - (free_space.free_space - (1.5 * event_table_size.size ))) as required FROM 
                (SELECT 1 as jc, 'event_table_size', sum(bytes) as size FROM system.parts WHERE table = 'sharded_events') event_table_size
            JOIN 
                (SELECT 1 as jc, 'free_disk_space', free_space, total_space as size FROM system.disks WHERE name = 'default') free_space
            ON event_table_size.jc=free_space.jc
            """
            )
            required_space = result[0][0]
            return (False, f"Upgrade your ClickHouse storage to at least {required_space}.")

    def progress(self, _):
        result = sync_execute(f"SELECT COUNT(1) FROM {TEMPORARY_TABLE_NAME}")
        result2 = sync_execute(f"SELECT COUNT(1) FROM {EVENTS_TABLE}")
        total_events_to_move = result2[0][0]
        total_events_moved = result[0][0]

        progress = 100 * (total_events_moved / total_events_to_move)
        return progress
