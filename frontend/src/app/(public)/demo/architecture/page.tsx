"use client";

// Public route: /demo/architecture
// Live, interactive node-graph of how a transaction flows through ORGON.
// No auth required — designed for cold sales meetings + marketing share.

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Icon } from "@/lib/icons";
import { GraphCanvas } from "@/components/demo-simulator/GraphCanvas";
import { ScenarioPlayer } from "@/components/demo-simulator/panels/ScenarioPlayer";
import { NodeDetailPanel } from "@/components/demo-simulator/panels/NodeDetailPanel";
import type { NodeData } from "@/components/demo-simulator/graph-config";
import type { Scenario, ScenarioStep } from "@/components/demo-simulator/scenarios/types";

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
  const [runKey, setRunKey] = useState(0);
  const [step, setStep] = useState<ScenarioStep | null>(null);
  const [stepIdx, setStepIdx] = useState(-1);
  const [selectedNode, setSelectedNode] = useState<NodeData | null>(null);

  const current = useMemo(
    () => SCENARIOS.find((s) => s.id === scenarioId) ?? SCENARIOS[0],
    [scenarioId],
  );

  const handleStep = useCallback((s: ScenarioStep | null, i: number) => {
    setStep(s);
    setStepIdx(i);
  }, []);

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
          <span className="hidden sm:inline">
            Интерактивная схема работы платформы — все ноды и связи реальные, соответствуют коду.
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

      {/* Summary strip */}
      <div className="shrink-0 px-5 py-3 border-b border-border bg-muted/30">
        <div className="max-w-[1400px] mx-auto flex items-start gap-4">
          <Icon icon="solar:info-circle-bold" className="shrink-0 mt-0.5 text-[16px] text-primary" />
          <p className="text-[12px] text-foreground leading-snug">
            <span className="font-medium">{current.title}.</span>{" "}
            <span className="text-muted-foreground">{current.summary}</span>
          </p>
        </div>
      </div>

      {/* Graph area takes the remaining space */}
      <div className="flex-1 min-h-0 relative">
        <GraphCanvas
          scenario={current}
          runKey={runKey}
          onStep={handleStep}
          onNodeSelect={setSelectedNode}
        />
        <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
      </div>

      {/* Bottom player */}
      <ScenarioPlayer
        scenarios={SCENARIOS}
        current={current}
        onSelect={(s) => {
          setScenarioId(s.id);
          setRunKey((k) => k + 1);
        }}
        onRestart={() => setRunKey((k) => k + 1)}
        step={step}
        stepIndex={stepIdx}
      />
    </div>
  );
}
