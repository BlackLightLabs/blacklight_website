/**
 * Agent Builder API Client
 *
 * Handles communication with the FastAPI backend including:
 * - Chat-based agent creation with streaming responses
 * - Agent management (list, get, execute)
 * - Server-Sent Events (SSE) for real-time token streaming
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Message role types for chat conversations
 */
export type MessageRole = "user" | "assistant" | "system";

/**
 * Agent build/execution status types
 */
export type AgentStatus =
  | "PLANNING"
  | "BUILDING"
  | "READY"
  | "FAILED"
  | "RUNNING"
  | "COMPLETED"
  | "ERROR";

/**
 * Node types in the agent graph
 */
export interface NodeSpec {
  id: string;
  type: string;
  data: {
    label: string;
    description?: string;
    [key: string]: unknown;
  };
}

/**
 * Edge types in the agent graph
 */
export interface EdgeSpec {
  id: string;
  source: string;
  target: string;
  data?: {
    condition?: string;
    [key: string]: unknown;
  };
}

/**
 * Agent graph structure
 */
export interface AgentGraph {
  nodes: NodeSpec[];
  edges: EdgeSpec[];
}

/**
 * Chat message in a conversation
 */
export interface ChatMessage {
  role: MessageRole;
  content: string;
}

/**
 * Agent details returned from the API
 */
export interface AgentDetails {
  agent_id: string;
  status: AgentStatus;
  description: string;
  created_at: string;
  graph_structure?: AgentGraph;
  estimated_cost_per_run?: number;
  total_executions: number;
  total_cost: number;
}

/**
 * Response from non-streaming chat endpoint
 */
export interface ChatResponse {
  agent_id: string | null;
  message: string;
  agent_ready: boolean;
  agent_details: AgentDetails | null;
}

/**
 * Request to execute an agent
 */
export interface AgentExecuteRequest {
  agent_id: string;
  input_data?: Record<string, unknown>;
  user_id?: string;
}

/**
 * Response from agent execution
 */
export interface AgentExecuteResponse {
  execution_id: string;
  agent_id: string;
  status: AgentStatus;
  result?: Record<string, unknown>;
  cost?: number;
  started_at: string;
  completed_at?: string;
}

/**
 * Callbacks for handling Server-Sent Events during agent creation streaming
 */
export interface StreamCallbacks {
  /** Called when a new token is received from the LLM */
  onToken?: (token: string) => void;

  /** Called when the assistant is processing/thinking (no visible tokens yet) */
  onThinking?: (message: string) => void;

  /** Called when the agent graph structure is updated */
  onGraphUpdate?: (graph: AgentGraph) => void;

  /** Called when the agent build process starts */
  onBuildStarted?: (agentId: string) => void;

  /** Called with build progress updates (stage name and percentage) */
  onBuildProgress?: (stage: string, progress: number) => void;

  /** Called when an agent ID is assigned to the conversation */
  onAgentId?: (agentId: string) => void;

  /** Called when the agent build is complete and ready for use */
  onAgentReady?: (agentId: string) => void;

  /** Called with full agent details after successful creation */
  onAgentDetails?: (details: AgentDetails) => void;

  /** Called when the stream is complete */
  onDone?: () => void;

  /** Called if an error occurs during streaming */
  onError?: (error: string) => void;
}

/**
 * API client for communicating with the Agent Builder backend
 */
export const api = {
  /**
   * Send a chat message for agent creation (non-streaming)
   *
   * @param message - User's chat message
   * @param conversationHistory - Previous messages in the conversation
   * @param agentId - ID of the agent being created (null for new conversations)
   * @returns Promise resolving to chat response with agent details
   * @throws Error if API request fails
   *
   * @deprecated Use chatForAgentCreationStream for better UX with real-time responses
   */
  async chatForAgentCreation(
    message: string,
    conversationHistory: ChatMessage[] = [],
    agentId: string | null = null
  ): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/api/agents/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include", // Include httpOnly cookies
      body: JSON.stringify({
        message,
        conversation_history: conversationHistory,
        agent_id: agentId,
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Stream chat responses for agent creation using Server-Sent Events (SSE)
   *
   * Provides real-time token-by-token streaming similar to ChatGPT.
   * The backend uses LangChain's streaming callbacks to send tokens as they're generated.
   *
   * @param message - User's chat message
   * @param conversationHistory - Previous messages in the conversation
   * @param agentId - ID of the agent being created (null for new conversations)
   * @param callbacks - Event handlers for different SSE event types
   */
  async chatForAgentCreationStream(
    message: string,
    conversationHistory: ChatMessage[] = [],
    agentId: string | null = null,
    callbacks: StreamCallbacks = {}
  ): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/agents/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include", // Include httpOnly cookies
      body: JSON.stringify({
        message,
        conversation_history: conversationHistory,
        agent_id: agentId,
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("Response body is not readable");
    }

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            try {
              const event = JSON.parse(data);

              switch (event.type) {
                case "agent_id":
                  callbacks.onAgentId?.(event.agent_id);
                  break;
                case "token":
                  callbacks.onToken?.(event.content);
                  break;
                case "thinking":
                  callbacks.onThinking?.(event.message);
                  break;
                case "graph_update":
                  callbacks.onGraphUpdate?.(event.graph);
                  break;
                case "build_started":
                  callbacks.onBuildStarted?.(event.agent_id);
                  break;
                case "build_progress":
                  callbacks.onBuildProgress?.(event.stage, event.progress);
                  break;
                case "agent_ready":
                  callbacks.onAgentReady?.(event.agent_id);
                  break;
                case "agent_details":
                  callbacks.onAgentDetails?.(event.details);
                  break;
                case "done":
                  callbacks.onDone?.();
                  break;
                case "error":
                  callbacks.onError?.(event.message);
                  break;
              }
            } catch (e) {
              console.error("Failed to parse SSE data:", data, e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  /**
   * List all agents created by the current user
   *
   * @returns Promise resolving to array of agent details
   * @throws Error if API request fails
   */
  async listAgents(): Promise<AgentDetails[]> {
    const response = await fetch(`${API_BASE_URL}/api/agents/`, {
      credentials: "include", // Include httpOnly cookies
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Get details for a specific agent
   *
   * @param agentId - UUID of the agent to retrieve
   * @returns Promise resolving to agent details
   * @throws Error if API request fails or agent not found
   */
  async getAgent(agentId: string): Promise<AgentDetails> {
    const response = await fetch(`${API_BASE_URL}/api/agents/${agentId}`, {
      credentials: "include", // Include httpOnly cookies
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Execute an agent with provided input data
   *
   * @param request - Execution request containing agent_id and input_data
   * @returns Promise resolving to execution response with results
   * @throws Error if API request fails or agent is not ready
   */
  async executeAgent(request: AgentExecuteRequest): Promise<AgentExecuteResponse> {
    const response = await fetch(`${API_BASE_URL}/api/agents/execute`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include", // Include httpOnly cookies
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  },
};
