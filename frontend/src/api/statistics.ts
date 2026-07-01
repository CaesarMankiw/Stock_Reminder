import { apiRequest, toQuery } from "./client";
import type { AnchorStatistics, PeriodStatistics } from "../types/api";

export function fetchAnchorStatistics(
  assetId: number,
  params: { anchorDate: string; latestBasis: "latest_close" | "today_open" },
): Promise<AnchorStatistics> {
  return apiRequest<AnchorStatistics>(
    `/api/assets/${assetId}/statistics/anchor${toQuery({
      anchor_date: params.anchorDate,
      latest_basis: params.latestBasis,
    })}`,
  );
}

export function fetchPeriodStatistics(
  assetId: number,
  params: {
    period: "1w" | "1m" | "3m" | "1y" | "custom";
    startDate?: string;
    endDate?: string;
  },
): Promise<PeriodStatistics> {
  return apiRequest<PeriodStatistics>(
    `/api/assets/${assetId}/statistics/period${toQuery({
      period: params.period,
      start_date: params.startDate,
      end_date: params.endDate,
    })}`,
  );
}
