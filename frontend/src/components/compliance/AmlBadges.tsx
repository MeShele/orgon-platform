// Severity + status badges for AML triage.
// Colour-tokens map onto Crimson Ledger v2 palette already wired in
// the project — no new tailwind classes.

import { Badge } from "@/components/ui/Badge";
import type { AmlSeverity, AmlStatus } from "@/lib/amlAlerts";

const SEVERITY_LABELS: Record<AmlSeverity, string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  critical: "Критический",
};

const SEVERITY_VARIANT: Record<AmlSeverity, "gray" | "warning" | "danger" | "primary"> = {
  low: "gray",
  medium: "primary",
  high: "warning",
  critical: "danger",
};

export function AmlSeverityBadge({ severity }: { severity: AmlSeverity }) {
  return (
    <Badge variant={SEVERITY_VARIANT[severity]} mono>
      {SEVERITY_LABELS[severity]}
    </Badge>
  );
}

const STATUS_LABELS: Record<AmlStatus, string> = {
  open: "Открыт",
  investigating: "В работе",
  resolved: "Решён",
  false_positive: "Ложное",
  reported: "В регулятор",
};

const STATUS_VARIANT: Record<AmlStatus, "warning" | "primary" | "success" | "gray" | "navy"> = {
  open: "warning",
  investigating: "primary",
  resolved: "success",
  false_positive: "gray",
  reported: "navy",
};

export function AmlStatusBadge({ status }: { status: AmlStatus }) {
  return (
    <Badge variant={STATUS_VARIANT[status]}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}
