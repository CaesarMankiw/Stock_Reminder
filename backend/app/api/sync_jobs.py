from datetime import date

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.db.connection import connect
from app.db.repositories import SyncJobRepository
from app.db.schema import initialize_schema
from app.services.sync_service import SyncService


router = APIRouter(prefix="/api/sync-jobs", tags=["sync-jobs"])


class RunSyncPayload(BaseModel):
    job_type: str = "init_history"
    asset_id: int | None = None
    market: str | None = None
    target_date: date | None = None
    years: int = 5


@router.get("")
def list_sync_jobs(
    job_type: str | None = None,
    status: str | None = None,
    asset_id: int | None = None,
    limit: int = 100,
) -> list[dict[str, object]]:
    with connect() as connection:
        initialize_schema(connection)
        jobs = SyncJobRepository(connection).list_jobs(
            job_type=job_type,
            status=status,
            asset_id=asset_id,
            limit=limit,
        )
        return [job.to_dict() for job in jobs]


@router.post("/run")
def run_sync_job(payload: RunSyncPayload) -> list[dict[str, object]]:
    service = SyncService()
    try:
        if payload.job_type == "init_history":
            results = service.sync_history(
                years=max(1, min(payload.years, 5)),
                market=payload.market,
                asset_id=payload.asset_id,
            )
        elif payload.job_type == "open_sync":
            results = service.sync_open(
                target_date=payload.target_date,
                market=payload.market,
                asset_id=payload.asset_id,
            )
        elif payload.job_type == "close_sync":
            results = service.sync_close(
                target_date=payload.target_date,
                market=payload.market,
                asset_id=payload.asset_id,
            )
        else:
            raise HTTPException(status_code=400, detail="job_type must be init_history, open_sync, or close_sync")
    finally:
        service.close()
    return [result.to_dict() for result in results]
