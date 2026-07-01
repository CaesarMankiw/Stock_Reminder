import { apiRequest, toQuery } from "./client";
import type { Asset, AssetSummary } from "../types/api";

export function fetchAssets(activeOnly = false): Promise<Asset[]> {
  return apiRequest<Asset[]>(`/api/assets${toQuery({ active_only: activeOnly })}`);
}

export function fetchAssetSummaries(activeOnly = false): Promise<AssetSummary[]> {
  return apiRequest<AssetSummary[]>(`/api/assets/summary${toQuery({ active_only: activeOnly })}`);
}

export function fetchAsset(assetId: number): Promise<Asset> {
  return apiRequest<Asset>(`/api/assets/${assetId}`);
}
