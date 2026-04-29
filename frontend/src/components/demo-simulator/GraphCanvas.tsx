"use client";

// Top-level canvas. Two visual modes:
//
//   * Ambient: every edge is animated with a slow flowing dash, all
//     nodes look "alive". The diagram never feels still.
//
//   * Focused: when a scenario step lands on a specific edge or node,
//     that element gets a stronger highlight (brighter color, thicker
//     stroke, faster dash, pulsing ring) layered on top of the
//     ambient animation.
//
// This makes the schema read like a living system rather than a
// turn-based replay.

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

import { COLUMN_LABELS, EDGES, NODES, type NodeData } from "./graph-config";
import { OrgonNode } from "./nodes/OrgonNode";
import type { Scenario, ScenarioStep } from "./scenarios/types";

const NODE_TYPES = { orgon: OrgonNode };

// Tone → color used for the focused (active step) edge.
const TONE_STROKE: Record<NonNullable<ScenarioStep["tone"]>, string> = {
  default: "var(--primary)",
  success: "var(--success)",
  warning: "rgb(217 119 6)",
  danger:  "var(--destructive)",
  info:    "var(--primary)",
};

// Idle / ambient edge — every edge gets these by default.
// Animated dashes give a subtle "always something flowing" feel without
// being distracting.
const AMBIENT_EDGE_STYLE: React.CSSProperties = {
  stroke: "var(--border)",
  strokeWidth: 1.6,
  strokeDasharray: "4 6",
};

// Edge style for the currently-focused step. We override the ambient.
const focusedEdgeStyle = (
  tone: NonNullable<ScenarioStep["tone"]>,
): React.CSSProperties => ({
  stroke: TONE_STROKE[tone],
  strokeWidth: 3,
  strokeDasharray: "6 4",
  filter: "drop-shadow(0 0 6px rgba(156,24,37,0.32))",
});

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
  // Initial nodes/edges already carry the ambient animated style.
  const [nodes, setNodes] = useState<Node<NodeData>[]>(NODES);
  const [edges, setEdges] = useState<Edge[]>(() =>
    EDGES.map((e) => ({ ...e, animated: true, style: AMBIENT_EDGE_STYLE })),
  );
  const stepIdxRef = useRef(0);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  // Reset all node/edge highlights to the ambient idle state.
  const resetHighlights = useCallback(() => {
    setNodes((prev) =>
      prev.map((n) => ({ ...n, data: { ...n.data, active: false, halt: false } })),
    );
    setEdges(
      EDGES.map((e) => ({ ...e, animated: true, style: AMBIENT_EDGE_STYLE })),
    );
  }, []);

  // Apply visual emphasis for one scenario step.
  const applyStep = useCallback((step: ScenarioStep) => {
    const tone = step.tone ?? "default";

    if (step.kind === "edge" && step.from && step.to) {
      const edgeId = `${step.from}__${step.to}`;
      setEdges((prev) =>
        prev.map((e) =>
          e.id === edgeId
            ? { ...e, animated: true, style: focusedEdgeStyle(tone) }
            // Other edges fall back to ambient (so the focused one stands out).
            : { ...e, animated: true, style: AMBIENT_EDGE_STYLE },
        ),
      );
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
        prev.map((e) => ({ ...e, animated: true, style: AMBIENT_EDGE_STYLE })),
      );
    } else if (step.kind === "halt" && step.node) {
      setNodes((prev) =>
        prev.map((n) => ({
          ...n,
          data: { ...n.data, active: n.id === step.node, halt: n.id === step.node },
        })),
      );
      setEdges((prev) =>
        prev.map((e) => ({ ...e, animated: true, style: AMBIENT_EDGE_STYLE })),
      );
    } else if (step.kind === "wait") {
      // Hold whatever was applied last.
    }
  }, []);

  // Schedule the scenario as a chain of setTimeouts and loop it.
  useEffect(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    stepIdxRef.current = 0;
    resetHighlights();
    onStep?.(null, -1);

    let cumulative = 400;
    scenario.steps.forEach((step, i) => {
      const t = setTimeout(() => {
        stepIdxRef.current = i;
        applyStep(step);
        onStep?.(step, i);
      }, cumulative);
      timersRef.current.push(t);
      cumulative += step.durationMs ?? 1500;
    });
    // Cool-down + idle hold before the next loop iteration.
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

  const proOptions = useMemo(() => ({ hideAttribution: true }), []);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={NODE_TYPES}
      proOptions={proOptions}
      // Default viewport — chosen so 4 columns fit nicely without the
      // "ant-sized nodes" effect of fitView.
      defaultViewport={{ x: 20, y: 30, zoom: 0.9 }}
      minZoom={0.5}
      maxZoom={1.4}
      panOnScroll
      nodesDraggable={false}
      elementsSelectable={true}
      onNodeClick={(_, node) => onNodeSelect?.(node.data as NodeData)}
      className="bg-background"
    >
      <Background gap={28} size={1.2} color="var(--border)" />

      {/* Floating column headers, rendered as React Flow content layer */}
      {COLUMN_LABELS.map((c) => (
        <div
          key={c.label}
          className="pointer-events-none absolute z-10"
          style={{ left: c.x, top: -10, width: 300 }}
        >
          <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-faint">
            {c.label}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">{c.sub}</div>
        </div>
      ))}

      <Controls
        position="bottom-right"
        showInteractive={false}
        className="!shadow-none !rounded-md !border !border-border !bg-card"
      />
      <MiniMap
        position="bottom-left"
        pannable
        zoomable
        className="!rounded-md !border !border-border !bg-card"
        nodeColor={(n) => {
          const k = (n.data as NodeData).kind;
          if (k === "client" || k === "chain") return "var(--foreground)";
          if (k === "auth" || k === "external") return "var(--primary)";
          if (k === "policy") return "rgb(217 119 6)";
          if (k === "core") return "var(--success)";
          return "var(--muted-foreground)";
        }}
      />
    </ReactFlow>
  );
}

export function GraphCanvas(props: Props) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  );
}
