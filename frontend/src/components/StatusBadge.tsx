import type { ReactNode } from "react";

type StatusBadgeProps = {
  tone?: "neutral" | "good" | "warn" | "bad";
  children: ReactNode;
};

export function StatusBadge({ tone = "neutral", children }: StatusBadgeProps) {
  return <span className={`status-badge status-badge-${tone}`}>{children}</span>;
}
