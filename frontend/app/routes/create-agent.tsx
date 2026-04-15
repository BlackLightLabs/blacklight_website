import { useState } from "react";
import { useNavigate } from "react-router";
import type { Route } from "./+types/create-agent";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Alert, AlertDescription } from "../components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Textarea } from "../components/ui/textarea";
import { ChatContainer } from "../components/chat-container";
import { AgentGraphCanvasClient as AgentGraphCanvas } from "../components/agent-graph-canvas-client";
import { BuildStatusPanel, type BuildStage } from "../components/build-status-panel";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { toast } from "sonner";
import { api, type ChatMessage, type AgentDetails, type AgentGraph } from "../lib/api";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Create Agent - Agent Builder" },
    { name: "description", content: "Build your custom AI agent through conversation" },
  ];
}

/**
 * CreateAgent page - Split-screen conversational agent builder
 *
 * Left: Chat interface to describe agent requirements
 * Right: Visual graph showing agent structure being built
 * Bottom: Build progress status
 */
export default function CreateAgent() {
  const navigate = useNavigate();

  // Chat conversation state
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hi! I'm here to help you build a custom AI agent. Tell me what you'd like your agent to do. For example, you could say: 'I want an agent that checks my email daily for potential sales prospects, and continues down the sales pipeline'",
    },
  ]);

  // Agent state
  const [isLoading, setIsLoading] = useState(false);
  const [agentId, setAgentId] = useState<string | null>(null);
  const [createdAgent, setCreatedAgent] = useState<AgentDetails | null>(null);

  // Graph state
  const [agentGraph, setAgentGraph] = useState<AgentGraph>({ nodes: [], edges: [] });

  // Build status state
  const [buildStage, setBuildStage] = useState<BuildStage | null>(null);
  const [buildProgress, setBuildProgress] = useState(0);
  const [buildError, setBuildError] = useState<string | undefined>(undefined);

  // Test execution state
  const [showTestDialog, setShowTestDialog] = useState(false);
  const [testInput, setTestInput] = useState("");

  /**
   * Handles sending a message and streaming the AI response
   * Updates chat, graph, and build status in real-time
   */
  const handleSendMessage = async (message: string) => {
    if (!message.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: message,
    };

    // Add user message
    let assistantMessageIndex = 0;
    setMessages((prev) => {
      assistantMessageIndex = prev.length + 1;
      return [...prev, userMessage];
    });
    setIsLoading(true);

    // Add placeholder for streaming response
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      await api.chatForAgentCreationStream(message, messages, agentId, {
        onAgentId: (newAgentId) => {
          setAgentId(newAgentId);
        },
        onToken: (token) => {
          setMessages((prev) => {
            const updated = [...prev];
            updated[assistantMessageIndex] = {
              ...updated[assistantMessageIndex],
              content: updated[assistantMessageIndex].content + token,
            };
            return updated;
          });
        },
        onThinking: (thinkingMessage) => {
          // Replace assistant message with thinking message
          setMessages((prev) => {
            const updated = [...prev];
            updated[assistantMessageIndex] = {
              role: "assistant",
              content: `_${thinkingMessage}_`,
            };
            return updated;
          });
        },
        onGraphUpdate: (graph) => {
          setAgentGraph(graph);
        },
        onBuildStarted: () => {
          setBuildStage("code_generation");
          setBuildProgress(25);
        },
        onBuildProgress: (stage, progress) => {
          setBuildStage(stage as BuildStage);
          setBuildProgress(progress);
        },
        onAgentReady: (readyAgentId) => {
          setBuildStage("ready");
          setBuildProgress(100);
        },
        onAgentDetails: (details) => {
          setCreatedAgent(details);
          toast.success("Agent created successfully!", {
            description: "Your agent is ready to use.",
          });
        },
        onDone: () => {
          setIsLoading(false);
        },
        onError: (error) => {
          setBuildStage("failed");
          setBuildError(error);
          toast.error("Failed to build agent", {
            description: error,
          });
          setIsLoading(false);
        },
      });
    } catch (error) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[assistantMessageIndex] = {
          ...updated[assistantMessageIndex],
          content: "Sorry, I encountered an error. Please try again.",
        };
        return updated;
      });
      toast.error("Failed to process message", {
        description: "Please try again or refresh the page.",
      });
      console.error("Error:", error);
      setIsLoading(false);
    }
  };

  /**
   * Handles testing the created agent
   */
  const handleTestAgent = async () => {
    if (!createdAgent || !testInput.trim()) {
      toast.error("Please enter test input");
      return;
    }

    try {
      const result = await api.executeAgent({
        agent_id: createdAgent.agent_id,
        input_data: { input: testInput },
      });

      toast.success("Agent executed successfully!", {
        description: `Execution ID: ${result.execution_id}`,
      });

      // TODO: Show execution results in a dedicated panel or modal
      setShowTestDialog(false);
      setTestInput("");
    } catch (error) {
      toast.error("Failed to execute agent", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };

  return (
    <ProtectedRoute>
      <div className="flex h-full flex-col">
        {/* Success Alert - positioned at top */}
        {createdAgent && (
          <div className="absolute top-4 left-1/2 z-20 w-full max-w-2xl -translate-x-1/2 px-4">
            <Alert className="border-green-200 bg-green-50 shadow-lg dark:border-green-800 dark:bg-green-900/20">
              <AlertDescription>
                <div className="flex items-start gap-3">
                  <Badge variant="default" className="bg-green-600">
                    ✓ Success
                  </Badge>
                  <div className="flex-1">
                    <p className="mb-1 text-sm font-semibold text-green-800 dark:text-green-200">
                      Agent Created Successfully!
                    </p>
                    <p className="mb-3 text-sm text-green-700 dark:text-green-300">
                      {createdAgent.description}
                    </p>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => setShowTestDialog(true)}
                      >
                        Test Agent
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigate(`/agents/${createdAgent.agent_id}`)}
                      >
                        View Details
                      </Button>
                    </div>
                    <p className="mt-3 text-xs text-green-600 dark:text-green-400">
                      💬 Continue chatting below to refine your agent
                    </p>
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          </div>
        )}

        {/* Split-screen layout */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left: Chat Panel (40%) */}
          <div className="w-2/5 border-r">
            <ChatContainer
              messages={messages}
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              disabled={isLoading}
              placeholder={
                createdAgent
                  ? "Ask to refine your agent (e.g., 'Add error handling' or 'Make it faster')..."
                  : "Describe your agent..."
              }
              className="h-full"
            />
          </div>

          {/* Right: Graph Panel (60%) */}
          <div className="flex-1">
            <AgentGraphCanvas nodes={agentGraph.nodes} edges={agentGraph.edges} />
          </div>
        </div>

        {/* Bottom: Build Status Panel */}
        <BuildStatusPanel
          stage={buildStage}
          progress={buildProgress}
          error={buildError}
        />

        {/* Test Agent Dialog */}
        <Dialog open={showTestDialog} onOpenChange={setShowTestDialog}>
          <DialogContent className="sm:max-w-[525px]">
            <DialogHeader>
              <DialogTitle>Test Your Agent</DialogTitle>
              <DialogDescription>
                Run your agent with test input to see how it performs.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <label htmlFor="test-input" className="text-sm font-medium">
                  Test Input
                </label>
                <Textarea
                  id="test-input"
                  placeholder="Enter test input for your agent..."
                  value={testInput}
                  onChange={(e) => setTestInput(e.target.value)}
                  rows={4}
                  className="resize-none"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={() => setShowTestDialog(false)}>
                  Cancel
                </Button>
                <Button onClick={handleTestAgent}>
                  Run Test
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </ProtectedRoute>
  );
}
