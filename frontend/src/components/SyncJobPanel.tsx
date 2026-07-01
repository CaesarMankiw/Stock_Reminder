import type { SyncJob } from "../types/api";
import { formatDateTime } from "../utils/format";
import { StatusBadge } from "./StatusBadge";

type SyncJobPanelProps = {
  jobs: SyncJob[];
};

export function SyncJobPanel({ jobs }: SyncJobPanelProps) {
  return (
    <section className="surface sync-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Sync</p>
          <h2>同步状态</h2>
        </div>
      </div>
      {jobs.length === 0 ? <p className="empty-state">暂无同步任务。</p> : null}
      <div className="sync-list">
        {jobs.map((job) => (
          <article className="sync-item" key={job.id}>
            <div>
              <strong>{job.job_type}</strong>
              <p>{job.provider_symbol ?? "all assets"} / rows {job.row_count}</p>
              {job.error_message ? <p className="error-text">{job.error_message}</p> : null}
            </div>
            <div className="sync-meta">
              <StatusBadge tone={job.status === "success" ? "good" : job.status === "failed" ? "bad" : "warn"}>
                {job.status}
              </StatusBadge>
              <span>{formatDateTime(job.finished_at ?? job.started_at)}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
