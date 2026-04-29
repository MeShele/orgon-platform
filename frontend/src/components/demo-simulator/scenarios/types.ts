// Scenario data model. JSON files in this folder must satisfy these types.
// Each scenario is a sequence of steps; each step lights up an edge or
// activates a node, with optional message and outcome.

export type StepKind =
  | "edge"      // animate a packet along an edge from→to
  | "node"      // pulse a node (e.g. it does internal work)
  | "halt"      // hard-stop the flow with a red mark (sanctions hit, replay reject)
  | "branch"    // visually fork a flow (used for retry / multi-tenant)
  | "wait";     // dwell with no animation (use to pace narration)

export interface ScenarioStep {
  kind: StepKind;

  /** edge endpoints — for kind="edge" */
  from?: string;
  to?: string;

  /** for kind="node" / "halt" */
  node?: string;

  /** Russian narration shown in the player while this step is on screen. */
  caption: string;

  /** ms before moving on. Default 1500ms. */
  durationMs?: number;

  /** Visual tone of the packet / pulse. */
  tone?: "default" | "success" | "warning" | "danger" | "info";

  /** Optional payload preview (HTTP method/path, SQL snippet, JSON sample). */
  payload?: {
    label: string;          // e.g. "POST /api/transactions"
    body?: string;          // pretty-printed JSON / SQL
  };
}

export interface ScenarioPersona {
  /** Display name in the persona switcher. */
  label: string;
  /** ISO country code emoji prefix. */
  flag: string;
  /** One-line context: "криптообменник в Алматы, KZT/USDT". */
  context: string;
}

export interface Scenario {
  id: string;            // e.g. "withdrawal", "sanctions-block"
  title: string;
  summary: string;       // 1–2 sentences shown above the graph
  persona: ScenarioPersona;
  steps: ScenarioStep[];
}
