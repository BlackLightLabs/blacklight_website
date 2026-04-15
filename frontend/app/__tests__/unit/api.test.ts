/**
 * Unit tests for API client
 *
 * Tests all API client functions including fetch logic, error handling,
 * and SSE streaming functionality.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { api, type ChatMessage, type AgentDetails } from "../../lib/api";

describe("API Client", () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    global.fetch = mockFetch;
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("chatForAgentCreation", () => {
    it("should send chat message and return response", async () => {
      const mockResponse = {
        agent_id: "test-123",
        message: "Hello! How can I help?",
        agent_ready: false,
        agent_details: null,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await api.chatForAgentCreation("Hello", []);

      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/agents/chat",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it("should handle conversation history", async () => {
      const conversationHistory: ChatMessage[] = [
        { role: "user", content: "First message" },
        { role: "assistant", content: "First response" },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          agent_id: "test",
          message: "Ok",
          agent_ready: false,
          agent_details: null,
        }),
      });

      await api.chatForAgentCreation("Follow up", conversationHistory, "existing-123");

      const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(callBody.conversation_history).toEqual(conversationHistory);
      expect(callBody.agent_id).toBe("existing-123");
    });

    it("should throw error on failed request", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Server Error",
      });

      await expect(api.chatForAgentCreation("Test", [])).rejects.toThrow("API error: Server Error");
    });

    it("should handle null/empty inputs", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          agent_id: "test",
          message: "Ok",
          agent_ready: false,
          agent_details: null,
        }),
      });

      await api.chatForAgentCreation("", [], null);

      const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(callBody.message).toBe("");
      expect(callBody.conversation_history).toEqual([]);
      expect(callBody.agent_id).toBeNull();
    });
  });

  describe("chatForAgentCreationStream", () => {
    it("should stream tokens correctly", async () => {
      const tokens: string[] = [];
      let agentId: string | undefined;
      let agentReady = false;
      let done = false;

      // Mock SSE response
      const mockReader = {
        read: vi
          .fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"type":"agent_id","agent_id":"test-123"}\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"type":"token","content":"Hello"}\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"type":"token","content":" world"}\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"type":"done"}\n'),
          })
          .mockResolvedValueOnce({ done: true }),
        releaseLock: vi.fn(),
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: {
          getReader: () => mockReader,
        },
      });

      await api.chatForAgentCreationStream("Test message", [], null, {
        onAgentId: (id) => {
          agentId = id;
        },
        onToken: (token) => {
          tokens.push(token);
        },
        onAgentReady: () => {
          agentReady = true;
        },
        onDone: () => {
          done = true;
        },
      });

      expect(agentId).toBe("test-123");
      expect(tokens).toEqual(["Hello", " world"]);
      expect(done).toBe(true);
    });

    it("should handle streaming errors gracefully", async () => {
      let errorMessage: string | undefined;

      const mockReader = {
        read: vi
          .fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"type":"error","message":"Stream failed"}\n'),
          })
          .mockResolvedValueOnce({ done: true }),
        releaseLock: vi.fn(),
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: {
          getReader: () => mockReader,
        },
      });

      await api.chatForAgentCreationStream("Test", [], null, {
        onError: (error) => {
          errorMessage = error;
        },
      });

      expect(errorMessage).toBe("Stream failed");
    });

    it("should handle agent creation completion", async () => {
      let agentDetails: AgentDetails | undefined;
      let agentReadyId: string | undefined;

      const mockDetails = {
        agent_id: "created-123",
        status: "ready",
        description: "Test agent",
        created_at: new Date().toISOString(),
        total_executions: 0,
        total_cost: 0,
      };

      const mockReader = {
        read: vi
          .fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode(
              'data: {"type":"agent_ready","agent_id":"created-123"}\n'
            ),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode(
              `data: {"type":"agent_details","details":${JSON.stringify(mockDetails)}}\n`
            ),
          })
          .mockResolvedValueOnce({ done: true }),
        releaseLock: vi.fn(),
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: {
          getReader: () => mockReader,
        },
      });

      await api.chatForAgentCreationStream("Confirm", [], null, {
        onAgentReady: (id) => {
          agentReadyId = id;
        },
        onAgentDetails: (details) => {
          agentDetails = details;
        },
      });

      expect(agentReadyId).toBe("created-123");
      expect(agentDetails).toEqual(mockDetails);
    });

    it("should throw error if response body is not readable", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: null,
      });

      await expect(api.chatForAgentCreationStream("Test", [], null, {})).rejects.toThrow(
        "Response body is not readable"
      );
    });
  });

  describe("listAgents", () => {
    it("should fetch and return agents list", async () => {
      const mockAgents: AgentDetails[] = [
        {
          agent_id: "1",
          status: "READY",
          description: "Agent 1",
          created_at: new Date().toISOString(),
          total_executions: 5,
          total_cost: 2.5,
        },
        {
          agent_id: "2",
          status: "BUILDING",
          description: "Agent 2",
          created_at: new Date().toISOString(),
          total_executions: 0,
          total_cost: 0,
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAgents,
      });

      const result = await api.listAgents();

      expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/api/agents/");
      expect(result).toEqual(mockAgents);
    });

    it("should handle empty agents list", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      const result = await api.listAgents();
      expect(result).toEqual([]);
    });

    it("should throw error on failed request", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Not Found",
      });

      await expect(api.listAgents()).rejects.toThrow("API error: Not Found");
    });
  });

  describe("getAgent", () => {
    it("should fetch specific agent by ID", async () => {
      const mockAgent: AgentDetails = {
        agent_id: "specific-123",
        status: "READY",
        description: "Specific agent",
        created_at: new Date().toISOString(),
        total_executions: 10,
        total_cost: 5.0,
        graph_structure: {
          nodes: [
            { id: "1", type: "tool", data: { label: "Step 1" } },
            { id: "2", type: "tool", data: { label: "Step 2" } },
          ],
          edges: [{ id: "e1-2", source: "1", target: "2" }],
        },
        estimated_cost_per_run: 0.5,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAgent,
      });

      const result = await api.getAgent("specific-123");

      expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/api/agents/specific-123");
      expect(result).toEqual(mockAgent);
    });

    it("should handle non-existent agent", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Not Found",
      });

      await expect(api.getAgent("nonexistent")).rejects.toThrow();
    });
  });

  describe("executeAgent", () => {
    it("should execute agent with input data", async () => {
      const mockExecution = {
        execution_id: "exec-123",
        agent_id: "agent-456",
        status: "completed",
        result: { output: "Success" },
        cost: 0.5,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockExecution,
      });

      const result = await api.executeAgent({
        agent_id: "agent-456",
        input_data: { key: "value" },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/agents/execute",
        expect.objectContaining({
          method: "POST",
        })
      );
      expect(result).toEqual(mockExecution);
    });

    it("should execute agent without input data", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          execution_id: "exec-789",
          agent_id: "agent-456",
          status: "completed",
          started_at: new Date().toISOString(),
        }),
      });

      await api.executeAgent({ agent_id: "agent-456" });

      const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(callBody.agent_id).toBe("agent-456");
      expect(callBody.input_data).toBeUndefined();
    });

    it("should handle execution failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Agent not ready",
      });

      await expect(api.executeAgent({ agent_id: "not-ready" })).rejects.toThrow(
        "API error: Agent not ready"
      );
    });
  });
});
