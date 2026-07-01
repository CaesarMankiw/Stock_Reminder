import { apiRequest, toQuery } from "./client";
import type { DailyPrice } from "../types/api";

export function fetchPrices(
  assetId: number,
  params: { startDate?: string; endDate?: string } = {},
): Promise<DailyPrice[]> {
  return apiRequest<DailyPrice[]>(
    `/api/assets/${assetId}/prices${toQuery({
      start_date: params.startDate,
      end_date: params.endDate,
    })}`,
  );
}
