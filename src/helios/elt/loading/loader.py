from typing import Any, Protocol, runtime_checkable
from enum import StrEnum
from helios.elt.extraction.pipeline import TemporalResolution
from helios.elt.extraction.pipeline import Dataset
from dataclasses import dataclass

from helios.db.connector import DatabaseConnector
from helios.elt.loading.mapper import LoadingMapperFactory


class LoadStatus(StrEnum):
    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


@dataclass
class LoadingResult:
    """Summary of a staging load operation."""
    dataset: Dataset
    temporal_resolution: TemporalResolution
    target_table: str
    source_file: str
    rows_loaded: int = 0
    status: LoadStatus = LoadStatus.SUCCESS 
    error_message: str | None = None


@runtime_checkable
class Loader(Protocol):

    def load(self, data):
        "Load the given data into the target system."
        ...

class StagingLoader(Loader):

    def __init__(self, database_connector: DatabaseConnector):
        self.database_connector = database_connector

    def load(self, 
            data: list[dict[str, Any]],
            dataset: Dataset,
            temporal_resolution: TemporalResolution,
            source_file: str) -> LoadingResult:
        """Load the given data into the staging area."""
        if not data:
            mapper = LoadingMapperFactory.get_mapper(str(dataset))
            target_table = mapper.target_table 
            return LoadingResult(
                dataset=dataset,
                temporal_resolution=temporal_resolution,
                target_table=target_table,
                source_file=source_file,
                rows_loaded=0,
                status=LoadStatus.SKIPPED,
            )

        mapper = LoadingMapperFactory.get_mapper(str(dataset))
        insert_sql = mapper.insert_sql
        target_table = mapper.target_table
        mapped_data = mapper.map_batch(data=data,
                                       source_file=source_file,
                                       temporal_resolution=temporal_resolution)
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