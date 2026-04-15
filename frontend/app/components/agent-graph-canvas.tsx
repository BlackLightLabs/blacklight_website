import { useEffect, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from "@xyflow/react";
import type { Node, Edge } from "@xyflow/react";
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
 * Displays agent nodes and edges with custom styling for different node types.
 * Automatically layouts nodes using a simple tree algorithm.
 */
export function AgentGraphCanvas({ nodes = [], edges = [], className = "" }: AgentGraphCanvasProps) {
  const [isClient, setIsClient] = useState(false);
  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState([]);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState([]);

  // Only render on client to avoid SSR issues with React Flow
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Convert agent nodes to React Flow nodes with layout
  useEffect(() => {
    if (nodes.length === 0) {
      setFlowNodes([{
        id: "placeholder",
        type: "default",
        position: { x: 250, y: 100 },
        data: {
          label: (
            <div className="text-center text-muted-foreground">
              <p className="text-sm">Your agent graph will appear here</p>
              <p className="text-xs mt-1">Start chatting to build your agent</p>
            </div>
          ),
        },
        style: {
          width: 300,
          background: "hsl(var(--muted))",
          border: "1px dashed hsl(var(--border))",
          borderRadius: "8px",
          padding: "20px",
        },
      }]);
      return;
    }

    // Simple tree layout algorithm
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const positioned: Node[] = [];
    const levelWidth = 250;
    const levelHeight = 150;
    const startX = 50;
    const startY = 50;

    let currentY = startY;
    const processedNodes = new Set<string>();

    // Find entry nodes (nodes with no incoming edges)
    const incomingEdges = new Set(edges.map((e) => e.to));
    const entryNodes = nodes.filter((n) => !incomingEdges.has(n.id));

    // BFS to layout nodes
    const queue = [...entryNodes];
    let level = 0;

    while (queue.length > 0) {
      const levelSize = queue.length;
      let nodesInLevel = 0;

      for (let i = 0; i < levelSize; i++) {
        const node = queue.shift();
        if (!node || processedNodes.has(node.id)) continue;

        processedNodes.add(node.id);

        // Position node
        const x = level * levelWidth + startX;
        const y = nodesInLevel * levelHeight + currentY;

        positioned.push({
          id: node.id,
          type: node.type === "tool" ? "default" : node.type === "llm" ? "default" : "default",
          position: { x, y },
          data: {
            label: (
              <div className="text-sm">
                <div className="font-semibold mb-1">
                  {node.type === "tool" && "🔧 Tool"}
                  {node.type === "llm" && "🤖 LLM"}
                  {node.type === "conditional" && "🔀 Conditional"}
                </div>
                <div className="text-xs text-muted-foreground">
                  {node.tool || node.id}
                </div>
              </div>
            ),
          },
          style: {
            background:
              node.type === "tool"
                ? "hsl(var(--chart-1))"
                : node.type === "llm"
                  ? "hsl(var(--chart-2))"
                  : "hsl(var(--chart-3))",
            color: "hsl(var(--background))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "8px",
            padding: "12px",
            width: 180,
          },
        });

        nodesInLevel++;

        // Add children to queue
        const outgoingEdges = edges.filter((e) => e.from === node.id);
        for (const edge of outgoingEdges) {
          const childNode = nodeMap.get(edge.to);
          if (childNode && !processedNodes.has(childNode.id)) {
            queue.push(childNode);
          }
        }
      }

      level++;
    }

    setFlowNodes(positioned);
  }, [nodes, setFlowNodes]);

  // Convert agent edges to React Flow edges
  useEffect(() => {
    const flowEdges: Edge[] = edges.map((edge) => ({
      id: `${edge.from}-${edge.to}`,
      source: edge.from,
      target: edge.to,
      label: edge.condition || undefined,
      animated: true,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: "hsl(var(--primary))",
      },
      style: {
        stroke: "hsl(var(--primary))",
        strokeWidth: 2,
      },
      labelStyle: {
        fill: "hsl(var(--foreground))",
        fontSize: 10,
      },
      labelBgStyle: {
        fill: "hsl(var(--background))",
      },
    }));

    setFlowEdges(flowEdges);
  }, [edges, setFlowEdges]);

  // Return loading skeleton during SSR
  if (!isClient) {
    return (
      <div className={`h-full w-full flex items-center justify-center bg-muted/30 ${className}`}>
        <div className="text-center text-muted-foreground">
          <p className="text-sm">Loading graph visualization...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`h-full w-full ${className}`}>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        attributionPosition="bottom-left"
        className="bg-background"
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
      >
        <Background />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            return node.style?.background as string;
          }}
          className="!bg-muted border !border-border"
        />
      </ReactFlow>
    </div>
  );
}
