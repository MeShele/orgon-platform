"use client";

// Public route: /demo/architecture
// Two-column layout: living architecture graph on the left,
// vertical readable scenario timeline on the right. The graph never
// "plays through" — every edge has the same ambient flow animation.
// The right-side panel describes a chosen scenario as plain
// step-by-step text the visitor reads at their own pace.

import { useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Icon } from "@/lib/icons";
import { GraphCanvas } from "@/components/demo-simulator/GraphCanvas";
import { StepsTimeline } from "@/components/demo-simulator/panels/StepsTimeline";
import { NodeDetailPanel } from "@/components/demo-simulator/panels/NodeDetailPanel";
import type { NodeData } from "@/components/demo-simulator/graph-config";
import type { Scenario } from "@/components/demo-simulator/scenarios/types";

import withdrawalScenario     from "@/components/demo-simulator/scenarios/withdrawal.json";
import sanctionsBlockScenario from "@/components/demo-simulator/scenarios/sanctions-block.json";
import replayAttackScenario   from "@/components/demo-simulator/scenarios/replay-attack.json";
import rlsIsolationScenario   from "@/components/demo-simulator/scenarios/rls-isolation.json";
import nightWindowScenario    from "@/components/demo-simulator/scenarios/night-window.json";
import webhookRetryScenario   from "@/components/demo-simulator/scenarios/webhook-retry.json";

const SCENARIOS: Scenario[] = [
  withdrawalScenario     as Scenario,
  sanctionsBlockScenario as Scenario,
  replayAttackScenario   as Scenario,
  rlsIsolationScenario   as Scenario,
  nightWindowScenario    as Scenario,
  webhookRetryScenario   as Scenario,
];

export default function ArchitectureSimulatorPage() {
  const [scenarioId, setScenarioId] = useState<string>(SCENARIOS[0].id);
  const [selectedNode, setSelectedNode] = useState<NodeData | null>(null);

  const current = useMemo(
    () => SCENARIOS.find((s) => s.id === scenarioId) ?? SCENARIOS[0],
    [scenarioId],
  );

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Slim header */}
      <header className="shrink-0 h-14 border-b border-border bg-card flex items-center justify-between px-5">
        <Link href="/" className="flex items-center gap-2.5 text-foreground hover:text-primary transition-colors">
          <Image src="/orgon-icon.png" alt="" width={26} height={26} priority />
          <div className="leading-tight">
            <div className="font-mono text-[9px] tracking-[0.18em] text-faint">ASYSTEM</div>
            <div className="font-medium text-[13px] tracking-[0.06em]">ORGON · симулятор архитектуры</div>
          </div>
        </Link>

        <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
          <span className="hidden lg:inline">
            Все узлы и связи — реальные компоненты кода. Кликни на любой блок чтобы увидеть детали.
          </span>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-foreground hover:text-primary"
          >
            <Icon icon="solar:arrow-left-linear" className="text-[14px]" />
            На главную
          </Link>
        </div>
      </header>

      {/* Main split: graph (flex-1) + readable timeline (fixed 400px) */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        <div className="flex-1 min-w-0 relative">
          <GraphCanvas onNodeSelect={setSelectedNode} />
          <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
        </div>

        <StepsTimeline
          scenarios={SCENARIOS}
          current={current}
          onSelect={(s) => setScenarioId(s.id)}
        />
      </div>
    </div>
  );
}
