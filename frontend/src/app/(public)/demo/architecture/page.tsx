"use client";

// Public route: /demo/architecture
//
// Layout philosophy: page scrolls naturally. The graph column is
// sticky-positioned on lg+ screens so it stays visible while the
// reader scrolls through the right-side step list. On smaller
// screens the layout stacks: graph on top, steps below — also
// natural page scroll.
//
// React Flow does NOT capture mouse wheel — that's reserved for
// page scroll. Pan inside the graph by dragging; zoom with the
// on-screen controls.

import { useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Icon } from "@/lib/icons";
import { GraphCanvas } from "@/components/demo-simulator/GraphCanvas";
import { ColumnRail } from "@/components/demo-simulator/ColumnRail";
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
    <div className="min-h-screen bg-background">
      {/* Sticky page header — always visible while scrolling */}
      <header className="sticky top-0 z-30 h-14 border-b border-border bg-card flex items-center justify-between px-5">
        <Link
          href="/"
          className="flex items-center gap-2.5 text-foreground hover:text-primary transition-colors"
        >
          <Image src="/orgon-icon.png" alt="" width={26} height={26} priority />
          <div className="leading-tight">
            <div className="font-mono text-[9px] tracking-[0.18em] text-faint">ASYSTEM</div>
            <div className="font-medium text-[13px] tracking-[0.06em]">
              ORGON · симулятор архитектуры
            </div>
          </div>
        </Link>

        <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
          <span className="hidden lg:inline">
            Все узлы и связи — реальные компоненты кода. Кликни на любой блок чтобы увидеть детали.
          </span>
          <Link href="/" className="inline-flex items-center gap-1.5 text-foreground hover:text-primary">
            <Icon icon="solar:arrow-left-linear" className="text-[14px]" />
            На главную
          </Link>
        </div>
      </header>

      {/* Two-column body. On lg+ the graph is sticky and the steps
          panel scrolls naturally. On smaller screens both stack and
          flow with the page. */}
      <div className="lg:flex">
        {/* Graph column — sticky on lg+, fixed-height inside the viewport. */}
        <div
          className={[
            "flex-1 flex flex-col",
            "lg:sticky lg:top-14",
            "lg:h-[calc(100vh-3.5rem)]",
            "border-b lg:border-b-0 border-border",
          ].join(" ")}
        >
          <ColumnRail />
          <div className="flex-1 min-h-[520px] relative">
            <GraphCanvas onNodeSelect={setSelectedNode} />
            <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
          </div>
        </div>

        {/* Right side — flows with page scroll. */}
        <StepsTimeline
          scenarios={SCENARIOS}
          current={current}
          onSelect={(s) => setScenarioId(s.id)}
        />
      </div>
    </div>
  );
}
