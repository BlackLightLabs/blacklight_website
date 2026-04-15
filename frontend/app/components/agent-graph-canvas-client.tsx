import { useEffect, useState } from "react";
import type { Node, Edge } from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import "@xyflow/react/dist/style.css";

export interface AgentGraphNode {
  id: string;
  type: "tool" | "llm" | "conditional";
  tool?: string;
  prompt?: string;
  input?: string[];
  output?: string[];
  input_mapping?: Record<string, string>;
}

export interface AgentGraphEdge {
  from: string;
  to: string;
  condition?: string;
}

export interface AgentGraphCanvasProps {
  nodes?: AgentGraphNode[];
  edges?: AgentGraphEdge[];
  className?: string;
}

/**
 * AgentGraphCanvas - React Flow visualization of agent graph
 *
 * CLIENT-SIDE ONLY component that displays agent nodes and edges.
 * Uses dynamic imports to avoid SSR issues with React Flow.
 * Uses Dagre for professional hierarchical layout.
 */
export function AgentGraphCanvasClient({ nodes = [], edges = [], className = "" }: AgentGraphCanvasProps) {
  const [ReactFlowComponents, setReactFlowComponents] = useState<any>(null);
  const [flowNodes, setFlowNodes] = useState<Node[]>([]);
  const [flowEdges, setFlowEdges] = useState<Edge[]>([]);

  // Dynamically import React Flow only on client
  useEffect(() => {
    import("@xyflow/react").then((mod) => {
      setReactFlowComponents({
        ReactFlow: mod.ReactFlow,
        Background: mod.Background,
        Controls: mod.Controls,
        MiniMap: mod.MiniMap,
        MarkerType: mod.MarkerType,
        BackgroundVariant: mod.BackgroundVariant,
      });
    });
  }, []);

  /**
   * Get professional layout using Dagre
   */
  const getLayoutedElements = (
    nodes: AgentGraphNode[],
    edges: AgentGraphEdge[],
    direction = "TB"
  ): Node[] => {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    const nodeWidth = 200;
    const nodeHeight = 80;
    const isHorizontal = direction === "LR";

    dagreGraph.setGraph({
      rankdir: direction,
      nodesep: 80,      // Horizontal spacing between nodes
      ranksep: 100,     // Vertical spacing between ranks
      marginx: 40,      // Left/right margins
      marginy: 40,      // Top/bottom margins
    });

    // Add nodes to dagre
    nodes.forEach((node) => {
      dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    // Add edges to dagre
    edges.forEach((edge) => {
      dagreGraph.setEdge(edge.from, edge.to);
    });

    // Calculate layout
    dagre.layout(dagreGraph);

    // Convert to React Flow nodes with calculated positions
    return nodes.map((node) => {
      const nodeWithPosition = dagreGraph.node(node.id);

      return {
        id: node.id,
        type: "default",
        targetPosition: isHorizontal ? ("left" as const) : ("top" as const),
        sourcePosition: isHorizontal ? ("right" as const) : ("bottom" as const),
        position: {
          x: nodeWithPosition.x - nodeWidth / 2,
          y: nodeWithPosition.y - nodeHeight / 2,
        },
        data: {
          label: (
            <div className="flex flex-col items-center justify-center h-full px-3 py-2">
              <div className="flex items-center gap-2 font-semibold text-sm mb-1">
                {node.type === "tool" && <span>🔧 Tool</span>}
                {node.type === "llm" && <span>🤖 LLM</span>}
                {node.type === "conditional" && <span>🔀 Conditional</span>}
              </div>
              <div className="text-xs font-medium opacity-90 text-center">
                {node.tool || node.id}
              </div>
            </div>
          ),
        },
        style: {
          background:
            node.type === "tool"
              ? "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" // Purple gradient for tools
              : node.type === "llm"
                ? "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)" // Pink gradient for LLMs
                : "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)", // Blue gradient for conditionals
          color: "#ffffff",
          border: "none",
          borderRadius: "12px",
          padding: "0",
          width: nodeWidth,
          height: nodeHeight,
          boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.15)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        },
      };
    });
  };

  // Convert agent nodes to React Flow nodes with Dagre layout
  useEffect(() => {
    if (!ReactFlowComponents) return;

    if (nodes.length === 0) {
      setFlowNodes([{
        id: "placeholder",
        type: "default",
        position: { x: 250, y: 150 },
        data: {
          label: (
            <div className="text-center text-muted-foreground px-6 py-4">
              <p className="text-base font-medium mb-2">Your agent graph will appear here</p>
              <p className="text-sm opacity-75">Start chatting to build your agent</p>
            </div>
          ),
        },
        style: {
          width: 350,
          height: 120,
          background: "transparent",
          border: "2px dashed hsl(var(--border))",
          borderRadius: "16px",
          padding: "0",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        },
        draggable: false,
      }]);
      return;
    }

    // Use Dagre for professional layout
    const layoutedNodes = getLayoutedElements(nodes, edges, "TB");
    setFlowNodes(layoutedNodes);
  }, [nodes, edges, ReactFlowComponents]);

  // Convert agent edges to React Flow edges with improved styling
  useEffect(() => {
    if (!ReactFlowComponents) return;

    const { MarkerType } = ReactFlowComponents;

    const flowEdges: Edge[] = edges.map((edge) => ({
      id: `${edge.from}-${edge.to}`,
      source: edge.from,
      target: edge.to,
      label: edge.condition || undefined,
      animated: true,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: "#8b5cf6",
        width: 25,
        height: 25,
      },
      style: {
        stroke: "#8b5cf6",
        strokeWidth: 3,
      },
      labelStyle: {
        fill: "#1f2937",
        fontSize: 12,
        fontWeight: 600,
      },
      labelBgStyle: {
        fill: "#ffffff",
        fillOpacity: 0.95,
      },
      labelBgPadding: [8, 4] as [number, number],
      labelBgBorderRadius: 4,
    }));

    setFlowEdges(flowEdges);
  }, [edges, ReactFlowComponents]);

  // Show loading state while React Flow is loading
  if (!ReactFlowComponents) {
    return (
      <div className={`h-full w-full flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 ${className}`}>
        <div className="text-center text-muted-foreground">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-sm font-medium">Loading graph visualization...</p>
        </div>
      </div>
    );
  }

  const { ReactFlow, Background, Controls, MiniMap, BackgroundVariant } = ReactFlowComponents;

  return (
    <div className={`h-full w-full ${className}`}>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        fitView
        fitViewOptions={{
          padding: 0.15,
          minZoom: 0.5,
          maxZoom: 1.5,
        }}
        attributionPosition="bottom-left"
        className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800"
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={true}
        minZoom={0.1}
        maxZoom={4}
        panOnDrag={true}
        zoomOnScroll={true}
        zoomOnPinch={true}
        zoomOnDoubleClick={false}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1.5}
          color="#94a3b8"
          className="opacity-30"
        />
        <Controls
          showZoom={true}
          showFitView={true}
          showInteractive={false}
          className="bg-white dark:bg-slate-800 shadow-lg border border-slate-200 dark:border-slate-700 rounded-lg"
        />
        <MiniMap
          nodeColor={(node: Node) => {
            const bg = node.style?.background as string;
            if (bg?.includes("gradient")) {
              // Extract first color from gradient for minimap
              return bg.includes("667eea") ? "#667eea" : bg.includes("f093fb") ? "#f093fb" : "#4facfe";
            }
            return bg || "#94a3b8";
          }}
          maskColor="rgba(0, 0, 0, 0.05)"
          className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg"
          pannable
          zoomable
        />
      </ReactFlow>
    </div>
  );
}
