"use client";

// Top-level canvas: renders the static node graph and runs scenarios
// step-by-step, animating edges and pulsing nodes. State is intentionally
// minimal (refs + useState) — we don't need a state library for this.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { EDGES, NODES, type NodeData } from "./graph-config";
import { OrgonNode } from "./nodes/OrgonNode";
import type { Scenario, ScenarioStep } from "./scenarios/types";

// React Flow needs a stable mapping of custom node types.
const NODE_TYPES = { orgon: OrgonNode };

// Tone → edge color/width while the packet is in transit.
const TONE_STROKE: Record<NonNullable<ScenarioStep["tone"]>, string> = {
  default: "var(--primary)",
  success: "var(--success)",
  warning: "rgb(217 119 6)",   // amber-600 — distinct from danger
  danger:  "var(--destructive)",
  info:    "var(--primary)",
};

interface Props {
  scenario: Scenario;
  /** Bumping this number restarts playback. */
  runKey: number;
  /** Notified when a step becomes active so the player can show its caption. */
  onStep?: (step: ScenarioStep | null, index: number) => void;
  /** Notified when the user clicks a node — for the detail drawer. */
  onNodeSelect?: (data: NodeData | null) => void;
}

function CanvasInner({ scenario, runKey, onStep, onNodeSelect }: Props) {
  // We mutate node data flags (active/halt) via React Flow's setNodes via state.
  const [nodes, setNodes] = useState<Node<NodeData>[]>(NODES);
  const [edges, setEdges] = useState<Edge[]>(EDGES);
  const stepIdxRef = useRef(0);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  // Reset all node/edge highlights to neutral.
  const resetHighlights = useCallback(() => {
    setNodes((prev) =>
      prev.map((n) => ({ ...n, data: { ...n.data, active: false, halt: false } })),
    );
    setEdges(EDGES.map((e) => ({ ...e })));
  }, []);

  // Apply a single step's visual: light up the relevant edge or node.
  const applyStep = useCallback((step: ScenarioStep) => {
    const tone = step.tone ?? "default";
    const stroke = TONE_STROKE[tone];

    if (step.kind === "edge" && step.from && step.to) {
      const edgeId = `${step.from}__${step.to}`;
      // Fade everything else, animate this edge.
      setEdges((prev) =>
        prev.map((e) =>
          e.id === edgeId
            ? {
                ...e,
                animated: true,
                style: {
                  stroke,
                  strokeWidth: 2.5,
                  filter: "drop-shadow(0 0 6px rgba(156,24,37,0.35))",
                },
              }
            : { ...e, animated: false, style: { stroke: "var(--border)", strokeWidth: 1.2, opacity: 0.45 } },
        ),
      );
      // Pulse both endpoint nodes for context.
      setNodes((prev) =>
        prev.map((n) => ({
          ...n,
          data: {
            ...n.data,
            active: n.id === step.from || n.id === step.to,
            halt: false,
          },
        })),
      );
    } else if (step.kind === "node" && step.node) {
      setNodes((prev) =>
        prev.map((n) => ({
          ...n,
          data: { ...n.data, active: n.id === step.node, halt: false },
        })),
      );
      setEdges((prev) =>
        prev.map((e) => ({ ...e, animated: false, style: { stroke: "var(--border)", strokeWidth: 1.2, opacity: 0.45 } })),
      );
    } else if (step.kind === "halt" && step.node) {
      setNodes((prev) =>
        prev.map((n) => ({
          ...n,
          data: { ...n.data, active: n.id === step.node, halt: n.id === step.node },
        })),
      );
      setEdges((prev) =>
        prev.map((e) => ({ ...e, animated: false, style: { stroke: "var(--border)", strokeWidth: 1.2, opacity: 0.45 } })),
      );
    } else if (step.kind === "wait") {
      // No visual change, just dwell with current highlights.
    }
  }, []);

  // Schedule the whole scenario as a chain of setTimeouts.
  // Avoids requestAnimationFrame overhead and survives tab-switching.
  useEffect(() => {
    // Clear any pending timers from a previous run.
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    stepIdxRef.current = 0;
    resetHighlights();
    onStep?.(null, -1);

    let cumulative = 300;          // 300ms head-room before the first step
    scenario.steps.forEach((step, i) => {
      const t = setTimeout(() => {
        stepIdxRef.current = i;
        applyStep(step);
        onStep?.(step, i);
      }, cumulative);
      timersRef.current.push(t);
      cumulative += step.durationMs ?? 1500;
    });
    // After the last step, hold briefly then reset the visual to neutral.
    const tEnd = setTimeout(() => {
      resetHighlights();
      onStep?.(null, scenario.steps.length);
    }, cumulative + 1200);
    timersRef.current.push(tEnd);

    return () => {
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
    };
  }, [scenario, runKey, applyStep, resetHighlights, onStep]);

  // Memoise styling props so React Flow doesn't see fresh refs every render.
  const proOptions = useMemo(() => ({ hideAttribution: true }), []);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={NODE_TYPES}
      proOptions={proOptions}
      fitView
      fitViewOptions={{ padding: 0.18 }}
      minZoom={0.4}
      maxZoom={1.5}
      panOnScroll
      nodesDraggable={false}
      elementsSelectable={true}
      onNodeClick={(_, node) => onNodeSelect?.(node.data as NodeData)}
      className="bg-background"
    >
      <Background gap={24} size={1} color="var(--border)" />
      <Controls
        position="bottom-right"
        showInteractive={false}
        className="!shadow-none !rounded-md !border !border-border !bg-card"
      />
      <MiniMap
        position="bottom-left"
        className="!rounded-md !border !border-border !bg-card"
        nodeColor={(n) => {
          const k = (n.data as NodeData).kind;
          if (k === "client" || k === "chain") return "var(--foreground)";
          if (k === "auth" || k === "external") return "var(--primary)";
          if (k === "policy") return "var(--warning, #d97706)";
          if (k === "core") return "var(--success)";
          return "var(--muted-foreground)";
        }}
      />
    </ReactFlow>
  );
}

// Small wrapper so the page doesn't have to import the provider.
export function GraphCanvas(props: Props) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  );
}
