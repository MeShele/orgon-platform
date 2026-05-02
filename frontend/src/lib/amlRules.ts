// AML monitoring-rules CRUD fetchers (Wave 25, Story 2.10).
//
// Endpoints under /api/v1/compliance/rules:
//   GET    /rules            list (RBAC-scoped)
//   POST   /rules            create
//   GET    /rules/{id}       read one
//   PATCH  /rules/{id}       partial update
//   DELETE /rules/{id}       hard delete

export type RuleType = "threshold" | "velocity" | "blacklist_address";
export type RuleAction = "alert" | "hold" | "block";
export type RuleSeverity = "low" | "medium" | "high" | "critical";

export interface MonitoringRule {
  id: string;
  organization_id: string | null;
  rule_name: string;
  rule_type: RuleType;
  description: string | null;
  rule_config: Record<string, unknown>;
  action: RuleAction;
  severity: RuleSeverity;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: number | null;
}

export interface MonitoringRuleCreate {
  organization_id?: string | null;
  rule_name: string;
  rule_type: RuleType;
  description?: string;
  rule_config: Record<string, unknown>;
  action?: RuleAction;
  severity?: RuleSeverity;
  is_active?: boolean;
}

export type MonitoringRuleUpdate = Partial<MonitoringRuleCreate>;

function authHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("orgon_access_token") : "";
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`AML rules request failed: ${res.status} ${body}`);
  }
  return (await res.json()) as T;
}

export async function fetchRules(): Promise<MonitoringRule[]> {
  const res = await fetch("/api/v1/compliance/rules", { headers: authHeaders() });
  return jsonOrThrow<MonitoringRule[]>(res);
}

export async function fetchRule(id: string): Promise<MonitoringRule> {
  const res = await fetch(`/api/v1/compliance/rules/${id}`, { headers: authHeaders() });
  return jsonOrThrow<MonitoringRule>(res);
}

export async function createRule(body: MonitoringRuleCreate): Promise<MonitoringRule> {
  const res = await fetch("/api/v1/compliance/rules", {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return jsonOrThrow<MonitoringRule>(res);
}

export async function updateRule(
  id: string,
  body: MonitoringRuleUpdate,
): Promise<MonitoringRule> {
  const res = await fetch(`/api/v1/compliance/rules/${id}`, {
    method: "PATCH",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return jsonOrThrow<MonitoringRule>(res);
}

export async function deleteRule(id: string): Promise<void> {
  const res = await fetch(`/api/v1/compliance/rules/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok && res.status !== 204) {
    const body = await res.text();
    throw new Error(`Delete rule failed: ${res.status} ${body}`);
  }
}
