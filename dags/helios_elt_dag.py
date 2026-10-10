import logging
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.exceptions import AirflowException

from helios.elt.extraction.pipeline import ExtractionResult, ExtractionStatus
from helios.elt.extraction.tasks import (
    extract_carbon_intensity,
    extract_electricity_demand,
    extract_electricity_generation,
    extract_installed_capacity,
    extract_power_sector_emissions,
)
from helios.elt.load.loader import LoadStatus, LoadingResult
from helios.elt.load.tasks import (
    load_carbon_intensity,
    load_electricity_demand,
    load_electricity_generation,
    load_installed_capacity,
    load_power_sector_emissions,
)
from helios.elt.transform.tasks import transform_dwh_core
from helios.elt.transform.transformer import TransformationResult, TransformationStatus

logger = logging.getLogger(__name__)

default_args = {
    "owner": "helios",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="helios_elt_pipeline",
    default_args=default_args,
    description="Helios ELT Pipeline: Ember API -> Bronze Lake -> Oracle STG -> DWH Core",
    schedule="0 4 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["helios", "energy", "oracle", "elt"],
)
def helios_elt_dag():
    # =========================================================================
    # Step 1: Extraction tasks (Parallel Fan-out)
    # =========================================================================
    @task
    def task_extract_generation() -> ExtractionResult:
        """Extract electricity generation data into Bronze Lake."""
        res = extract_electricity_generation()
        if res.status == ExtractionStatus.FAILED:
            raise AirflowException(f"Extraction failed for generation: {res.error_message}")
        return res

    @task
    def task_extract_capacity() -> ExtractionResult:
        """Extract installed capacity data into Bronze Lake."""
        res = extract_installed_capacity()
        if res.status == ExtractionStatus.FAILED:
            raise AirflowException(f"Extraction failed for capacity: {res.error_message}")
        return res

    @task
    def task_extract_carbon_intensity() -> ExtractionResult:
        """Extract carbon intensity data into Bronze Lake."""
        res = extract_carbon_intensity()
        if res.status == ExtractionStatus.FAILED:
            raise AirflowException(f"Extraction failed for carbon intensity: {res.error_message}")
        return res

    @task
    def task_extract_demand() -> ExtractionResult:
        """Extract electricity demand data into Bronze Lake."""
        res = extract_electricity_demand()
        if res.status == ExtractionStatus.FAILED:
            raise AirflowException(f"Extraction failed for demand: {res.error_message}")
        return res

    @task
    def task_extract_emissions() -> ExtractionResult:
        """Extract power sector emissions data into Bronze Lake."""
        res = extract_power_sector_emissions()
        if res.status == ExtractionStatus.FAILED:
            raise AirflowException(f"Extraction failed for emissions: {res.error_message}")
        return res

    # =========================================================================
    # Step 2: Staging Load tasks (Parallel Fan-out)
    # =========================================================================
    @task
    def task_load_generation(extract_result: ExtractionResult | None = None) -> LoadingResult:
        """Load generation data from Bronze Lake into STG_EMBER_GENERATION."""
        if extract_result:
            logger.info("Extraction status for generation: %s (%d records)", extract_result.status, extract_result.records_count)
        res = load_electricity_generation()
        if res.status == LoadStatus.FAILED:
            raise AirflowException(f"Staging load failed for generation: {res.error_message}")
        return res

    @task
    def task_load_capacity(extract_result: ExtractionResult | None = None) -> LoadingResult:
        """Load capacity data from Bronze Lake into STG_EMBER_CAPACITY."""
        if extract_result:
            logger.info("Extraction status for capacity: %s (%d records)", extract_result.status, extract_result.records_count)
        res = load_installed_capacity()
        if res.status == LoadStatus.FAILED:
            raise AirflowException(f"Staging load failed for capacity: {res.error_message}")
        return res

    @task
    def task_load_carbon_intensity(extract_result: ExtractionResult | None = None) -> LoadingResult:
        """Load carbon intensity data from Bronze Lake into STG_EMBER_CARBON_INTENSITY."""
        if extract_result:
            logger.info("Extraction status for carbon intensity: %s (%d records)", extract_result.status, extract_result.records_count)
        res = load_carbon_intensity()
        if res.status == LoadStatus.FAILED:
            raise AirflowException(f"Staging load failed for carbon intensity: {res.error_message}")
        return res

    @task
    def task_load_demand(extract_result: ExtractionResult | None = None) -> LoadingResult:
        """Load demand data from Bronze Lake into STG_EMBER_DEMAND."""
        if extract_result:
            logger.info("Extraction status for demand: %s (%d records)", extract_result.status, extract_result.records_count)
        res = load_electricity_demand()
        if res.status == LoadStatus.FAILED:
            raise AirflowException(f"Staging load failed for demand: {res.error_message}")
        return res

    @task
    def task_load_emissions(extract_result: ExtractionResult | None = None) -> LoadingResult:
        """Load emissions data from Bronze Lake into STG_EMBER_POWER_SECTOR_EMISSIONS."""
        if extract_result:
            logger.info("Extraction status for emissions: %s (%d records)", extract_result.status, extract_result.records_count)
        res = load_power_sector_emissions()
        if res.status == LoadStatus.FAILED:
            raise AirflowException(f"Staging load failed for emissions: {res.error_message}")
        return res

    # =========================================================================
    # Step 3: DWH Core Transformation (Synchronization Barrier)
    # =========================================================================
    @task
    def task_transform_dwh_core(load_results: list[LoadingResult] | None = None) -> TransformationResult:
        """Execute PKG_EMBER_ELT.f_load_all() in Oracle ADW to populate Core DWH."""
        res = transform_dwh_core(load_results=load_results)
        if str(res.status) == TransformationStatus.ERROR:
            raise AirflowException(f"DWH transformation failed: {res.error_message}")
        return res

    # =========================================================================
    # Pipeline Dependencies Definition
    # =========================================================================
    # 1. Trigger extraction
    ext_gen = task_extract_generation()
    ext_cap = task_extract_capacity()
    ext_ci = task_extract_carbon_intensity()
    # ext_dem = task_extract_demand()
    ext_emi = task_extract_emissions()

    # 2. Trigger loading into staging after extraction completes
    ld_gen = task_load_generation(extract_result=ext_gen)
    ld_cap = task_load_capacity(extract_result=ext_cap)
    ld_ci = task_load_carbon_intensity(extract_result=ext_ci)
    # ld_dem = task_load_demand(extract_result=ext_dem)
    ld_emi = task_load_emissions(extract_result=ext_emi)

    # 3. Trigger DWH transformation only after all 5 datasets are loaded
    task_transform_dwh_core(load_results=[ld_gen, ld_cap, ld_ci, ld_emi])


helios_dag = helios_elt_dag()
