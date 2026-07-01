from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncJob:
    id: int
    job_type: str
    asset_id: int | None
    provider: str | None
    provider_symbol: str | None
    status: str
    started_at: str
    finished_at: str | None
    row_count: int
    error_message: str | None
    retry_count: int
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "job_type": self.job_type,
            "asset_id": self.asset_id,
            "provider": self.provider,
            "provider_symbol": self.provider_symbol,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "row_count": self.row_count,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

