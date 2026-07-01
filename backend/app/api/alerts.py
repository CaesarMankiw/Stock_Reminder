from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.models.alert import AlertRuleInput
from app.services.alert_service import (
    AlertAssetNotFoundError,
    AlertRuleNotFoundError,
    AlertService,
    InvalidAlertRuleError,
)


router = APIRouter(tags=["alerts"])


class AlertRulePayload(BaseModel):
    asset_id: int
    name: str | None = None
    rule_type: str
    anchor_date: str | None = None
    period: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    latest_basis: str = "latest_close"
    trigger_metric: str = "change_pct"
    upper_threshold_pct: str | None = None
    lower_threshold_pct: str | None = None
    frequency: str = "once_per_data_date"
    is_enabled: bool = True

    def to_rule_input(self) -> AlertRuleInput:
        return AlertRuleInput(
            asset_id=self.asset_id,
            name=self.name,
            rule_type=self.rule_type,
            anchor_date=self.anchor_date,
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
            latest_basis=self.latest_basis,
            trigger_metric=self.trigger_metric,
            upper_threshold_pct=self.upper_threshold_pct,
            lower_threshold_pct=self.lower_threshold_pct,
            frequency=self.frequency,
            is_enabled=self.is_enabled,
        )


@router.post("/api/alert-rules")
def create_alert_rule(payload: AlertRulePayload) -> dict[str, object]:
    service = AlertService()
    try:
        return service.create_rule(payload.to_rule_input()).to_dict()
    except AlertAssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    except InvalidAlertRuleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        service.close()


@router.get("/api/alert-rules")
def list_alert_rules(
    asset_id: int | None = None,
    enabled_only: bool = False,
) -> list[dict[str, object]]:
    service = AlertService()
    try:
        return [
            rule.to_dict()
            for rule in service.list_rules(asset_id=asset_id, enabled_only=enabled_only)
        ]
    except AlertAssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    finally:
        service.close()


@router.get("/api/alert-rules/{rule_id}")
def get_alert_rule(rule_id: int) -> dict[str, object]:
    service = AlertService()
    try:
        return service.get_rule(rule_id).to_dict()
    except AlertRuleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Alert rule not found") from exc
    finally:
        service.close()


@router.put("/api/alert-rules/{rule_id}")
def update_alert_rule(rule_id: int, payload: AlertRulePayload) -> dict[str, object]:
    service = AlertService()
    try:
        return service.update_rule(rule_id, payload.to_rule_input()).to_dict()
    except AlertAssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    except AlertRuleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Alert rule not found") from exc
    except InvalidAlertRuleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        service.close()


@router.delete("/api/alert-rules/{rule_id}")
def delete_alert_rule(rule_id: int) -> dict[str, object]:
    service = AlertService()
    try:
        service.delete_rule(rule_id)
    except AlertRuleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Alert rule not found") from exc
    finally:
        service.close()
    return {"deleted": True, "rule_id": rule_id}


@router.post("/api/alerts/check")
def check_alerts(asset_id: int | None = None) -> dict[str, object]:
    service = AlertService()
    try:
        return service.check_alerts(asset_id=asset_id).to_dict()
    except AlertAssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    finally:
        service.close()


@router.get("/api/alert-events")
def list_alert_events(
    asset_id: int | None = None,
    rule_id: int | None = None,
    limit: int = 100,
) -> list[dict[str, object]]:
    service = AlertService()
    try:
        return [
            event.to_dict()
            for event in service.list_events(
                asset_id=asset_id,
                rule_id=rule_id,
                limit=limit,
            )
        ]
    except AlertAssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    except AlertRuleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Alert rule not found") from exc
    finally:
        service.close()
