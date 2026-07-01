from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from app.services.statistics_service import (
    LATEST_CLOSE,
    AssetNotFoundError,
    InvalidStatisticsRequest,
    StatisticsService,
)


router = APIRouter(prefix="/api/assets", tags=["statistics"])


@router.get("/{asset_id}/statistics/anchor")
def get_anchor_statistics(
    asset_id: int,
    anchor_date: date,
    latest_basis: str = LATEST_CLOSE,
) -> dict[str, object]:
    service = StatisticsService()
    try:
        statistics = service.get_anchor_statistics(
            asset_id=asset_id,
            anchor_date=anchor_date,
            latest_basis=latest_basis,
        )
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    except InvalidStatisticsRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        service.close()
    return statistics.to_dict()


@router.get("/{asset_id}/statistics/period")
def get_period_statistics(
    asset_id: int,
    period: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, object]:
    service = StatisticsService()
    try:
        statistics = service.get_period_statistics(
            asset_id=asset_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    except InvalidStatisticsRequest as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        service.close()
    return statistics.to_dict()
