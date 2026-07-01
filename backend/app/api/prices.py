from fastapi import APIRouter, HTTPException

from app.db.connection import connect
from app.db.repositories import AssetRepository, DailyPriceRepository
from app.db.schema import initialize_schema


router = APIRouter(prefix="/api/assets", tags=["prices"])


@router.get("/{asset_id}/prices")
def list_prices(
    asset_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, object]]:
    with connect() as connection:
        initialize_schema(connection)
        asset = AssetRepository(connection).get_by_id(asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="Asset not found")
        prices = DailyPriceRepository(connection).list_prices(
            asset_id=asset_id,
            start_date=start_date,
            end_date=end_date,
        )
        return [price.to_dict() for price in prices]

