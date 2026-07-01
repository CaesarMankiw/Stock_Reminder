from fastapi import APIRouter, HTTPException

from app.db.connection import connect
from app.db.repositories import AssetRepository, DailyPriceRepository
from app.db.schema import initialize_schema


router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("")
def list_assets(active_only: bool = False, market: str | None = None) -> list[dict[str, object]]:
    with connect() as connection:
        initialize_schema(connection)
        assets = AssetRepository(connection).list_assets(
            active_only=active_only,
            market=market,
        )
        return [asset.to_dict() for asset in assets]


@router.get("/summary")
def list_asset_summaries(active_only: bool = False) -> list[dict[str, object]]:
    with connect() as connection:
        initialize_schema(connection)
        assets = AssetRepository(connection).list_assets(active_only=active_only)
        prices = DailyPriceRepository(connection)
        summaries: list[dict[str, object]] = []
        for asset in assets:
            latest_complete = prices.get_latest_complete(asset.id)
            latest_open = prices.get_latest_open_record(asset.id)
            summaries.append(
                {
                    "asset": asset.to_dict(),
                    "latest_complete_date": latest_complete.trade_date if latest_complete else None,
                    "latest_complete_close": latest_complete.close if latest_complete else None,
                    "latest_open_date": latest_open.trade_date if latest_open else None,
                    "latest_open": latest_open.open if latest_open else None,
                    "latest_open_is_complete": latest_open.is_complete if latest_open else None,
                    "latest_fetched_at": latest_open.fetched_at if latest_open else None,
                    "price_count": prices.count_for_asset(asset.id),
                }
            )
        return summaries


@router.get("/{asset_id}")
def get_asset(asset_id: int) -> dict[str, object]:
    with connect() as connection:
        initialize_schema(connection)
        asset = AssetRepository(connection).get_by_id(asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="Asset not found")
        return asset.to_dict()
