import { apiRequest, toQuery } from "./client";
import type { AssetSyncResult, RunSyncPayload, SyncJob } from "../types/api";

export function fetchSyncJobs(limit = 8): Promise<SyncJob[]> {
  return apiRequest<SyncJob[]>(`/api/sync-jobs${toQuery({ limit })}`);
}

export function runSyncJob(payload: RunSyncPayload): Promise<AssetSyncResult[]> {
  return apiRequest<AssetSyncResult[]>("/api/sync-jobs/run", { method: "POST", body: payload });
}
