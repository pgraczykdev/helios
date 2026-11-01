from typing import Any

from helios.db.database_connector import DatabaseConnector
from helios.elt.extraction.models.dataset import Dataset
from helios.elt.extraction.models.temporal_resolution import TemporalResolution
from helios.elt.load.loader import Loader
from helios.elt.load.mappers.loading_mapper_factory import LoadingMapperFactory
from helios.elt.load.models.load_status import LoadStatus
from helios.elt.load.models.loading_result import LoadingResult


class StagingLoader(Loader):
    """Idempotent batch loader into Oracle STG_EMBER_* tables."""

    def __init__(self, database_connector: DatabaseConnector) -> None:
        self.database_connector = database_connector

    def load(
        self,
        data: list[dict[str, Any]],
        dataset: Dataset,
        temporal_resolution: TemporalResolution,
        source_file: str,
    ) -> LoadingResult:
        """Load the given data into the staging area."""
        if not data:
            mapper = LoadingMapperFactory.get_mapper(dataset=str(dataset))
            target_table = mapper.target_table
            return LoadingResult(
                dataset=dataset,
                temporal_resolution=temporal_resolution,
                target_table=target_table,
                source_file=source_file,
                rows_loaded=0,
                status=LoadStatus.SKIPPED,
            )

        mapper = LoadingMapperFactory.get_mapper(dataset=str(dataset))
        insert_sql = mapper.insert_sql
        target_table = mapper.target_table
        mapped_data = mapper.map_batch(
            data=data,
            source_file=source_file,
            temporal_resolution=temporal_resolution,
        )
        try:
            with self.database_connector.acquire_connection() as conn:
                with conn.cursor() as cursor:
                    delete_sql = f"DELETE FROM {target_table} WHERE source_file = :source_file"
                    cursor.execute(delete_sql, source_file=source_file)
                    cursor.executemany(insert_sql, mapped_data)
        except Exception as e:
            return LoadingResult(
                dataset=dataset,
                temporal_resolution=temporal_resolution,
                target_table=target_table,
                source_file=source_file,
                rows_loaded=0,
                status=LoadStatus.FAILED,
                error_message=str(e),
            )

        return LoadingResult(
            dataset=dataset,
            temporal_resolution=temporal_resolution,
            target_table=target_table,
            source_file=source_file,
            rows_loaded=len(mapped_data),
            status=LoadStatus.SUCCESS,
        )
