"use client";

// Static-but-living architecture diagram. Every edge has the same
// ambient flow animation; nothing "plays through". The diagram is a
// backdrop — readable documentation lives in the right panel.
//
// Click on any node to open the detail drawer (handled by the parent).

import { useMemo } from "react";
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

const NODE_TYPES = { orgon: OrgonNode };

// One ambient style for every edge. Animated dashes give the
// "always something flowing" feel. No highlighting on any specific
// step — that's intentional, the system is shown as living, not as a
// turn-based replay.
const AMBIENT_EDGE_STYLE: React.CSSProperties = {
  stroke: "var(--primary)",
  strokeWidth: 1.4,
  strokeDasharray: "4 6",
  opacity: 0.45,
};

interface Props {
  /** Notified when the user clicks a node — for the detail drawer. */
  onNodeSelect?: (data: NodeData | null) => void;
}

function CanvasInner({ onNodeSelect }: Props) {
  // Built once — there's no playback state any more, so we don't need
  // setNodes/setEdges. React Flow re-renders on resize via internal state.
  const nodes: Node<NodeData>[] = useMemo(() => NODES, []);
  const edges: Edge[] = useMemo(
    () => EDGES.map((e) => ({ ...e, animated: true, style: AMBIENT_EDGE_STYLE })),
    [],
  );

  const proOptions = useMemo(() => ({ hideAttribution: true }), []);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={NODE_TYPES}
      proOptions={proOptions}
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
