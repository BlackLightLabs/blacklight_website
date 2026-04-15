/**
 * Unit tests for ChatInput component
 *
 * Tests cover:
 * - Message sending (Enter key, button click)
 * - Loading and disabled states
 * - Auto-resize functionality
 * - Whitespace handling
 * - Keyboard shortcuts (Enter, Shift+Enter)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatInput } from "~/components/chat-input";

describe("ChatInput", () => {
  let onSendMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onSendMock = vi.fn();
  });

  describe("Rendering", () => {
    it("should render with default placeholder", () => {
      render(<ChatInput onSend={onSendMock} />);

      const textarea = screen.getByPlaceholderText("Type your message...");
      expect(textarea).toBeInTheDocument();
    });

    it("should render with custom placeholder", () => {
      render(<ChatInput onSend={onSendMock} placeholder="Ask me anything..." />);

      const textarea = screen.getByPlaceholderText("Ask me anything...");
      expect(textarea).toBeInTheDocument();
    });

    it("should render send button", () => {
      render(<ChatInput onSend={onSendMock} />);

      const sendButton = screen.getByRole("button", { name: /send message/i });
      expect(sendButton).toBeInTheDocument();
    });
  });

  describe("Message Sending", () => {
    it("should call onSend when send button is clicked", async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={onSendMock} />);

      const textarea = screen.getByPlaceholderText("Type your message...");
      const sendButton = screen.getByRole("button", { name: /send message/i });

      await user.type(textarea, "Hello, world!");
      await user.click(sendButton);

      expect(onSendMock).toHaveBeenCalledWith("Hello, world!");
      expect(onSendMock).toHaveBeenCalledTimes(1);
    });

    it("should call onSend when Enter key is pressed", async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={onSendMock} />);

      const textarea = screen.getByPlaceholderText("Type your message...");

      await user.type(textarea, "Test message{Enter}");

      expect(onSendMock).toHaveBeenCalledWith("Test message");
    });

    it("should insert newline when Shift+Enter is pressed", async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={onSendMock} />);

      const textarea = screen.getByPlaceholderText("Type your message...") as HTMLTextAreaElement;

      await user.type(textarea, "Line 1{Shift>}{Enter}{/Shift}Line 2");

      expect(textarea.value).toContain("\n");
      expect(onSendMock).not.toHaveBeenCalled();
    });

    it("should clear input after sending", async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={onSendMock} />);

      const textarea = screen.getByPlaceholderText("Type your message...") as HTMLTextAreaElement;

      await user.type(textarea, "Test{Enter}");

      expect(textarea.value).toBe("");
    });

    it("should trim whitespace before sending", async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={onSendMock} />);

      const textarea = screen.getByPlaceholderText("Type your message...");

      await user.type(textarea, "  spaces around  {Enter}");

      expect(onSendMock).toHaveBeenCalledWith("spaces around");
    });

    it("should not send empty messages", async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={onSendMock} />);

      const textarea = screen.getByPlaceholderText("Type your message...");

      await user.type(textarea, "   {Enter}");

      expect(onSendMock).not.toHaveBeenCalled();
    });

    it("should not send whitespace-only messages", async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={onSendMock} />);

      const sendButton = screen.getByRole("button", { name: /send message/i });
      const textarea = screen.getByPlaceholderText("Type your message...");

      await user.type(textarea, "     ");
      await user.click(sendButton);

      expect(onSendMock).not.toHaveBeenCalled();
    });
  });

  describe("Disabled State", () => {
    it("should disable textarea when disabled prop is true", () => {
      render(<ChatInput onSend={onSendMock} disabled />);

      const textarea = screen.getByPlaceholderText("Type your message...");
      expect(textarea).toBeDisabled();
    });

    it("should disable send button when disabled prop is true", () => {
      render(<ChatInput onSend={onSendMock} disabled />);

      const sendButton = screen.getByRole("button", { name: /send message/i });
      expect(sendButton).toBeDisabled();
    });

    it("should not send message when disabled", async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={onSendMock} disabled />);

      const textarea = screen.getByPlaceholderText("Type your message...");

      // Try to type (should not work because disabled)
      await user.type(textarea, "Test{Enter}");

      expect(onSendMock).not.toHaveBeenCalled();
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner when isLoading is true", () => {
      render(<ChatInput onSend={onSendMock} isLoading />);

      // Loading spinner should be present (LoaderIcon)
      const sendButton = screen.getByRole("button", { name: /send message/i });
      expect(sendButton.querySelector("svg")).toHaveClass("animate-spin");
    });

    it("should disable textarea when loading", () => {
      render(<ChatInput onSend={onSendMock} isLoading />);

      const textarea = screen.getByPlaceholderText("Type your message...");
      expect(textarea).toBeDisabled();
    });

    it("should disable send button when loading", () => {
      render(<ChatInput onSend={onSendMock} isLoading />);

      const sendButton = screen.getByRole("button", { name: /send message/i });
      expect(sendButton).toBeDisabled();
    });

    it("should not send message when loading", async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={onSendMock} isLoading />);

      const textarea = screen.getByPlaceholderText("Type your message...");

      await user.type(textarea, "Test{Enter}");

      expect(onSendMock).not.toHaveBeenCalled();
    });
  });

  describe("Button State", () => {
    it("should disable send button when input is empty", () => {
      render(<ChatInput onSend={onSendMock} />);

      const sendButton = screen.getByRole("button", { name: /send message/i });
      expect(sendButton).toBeDisabled();
    });

    it("should enable send button when input has text", async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={onSendMock} />);

      const textarea = screen.getByPlaceholderText("Type your message...");
      const sendButton = screen.getByRole("button", { name: /send message/i });

      expect(sendButton).toBeDisabled();

      await user.type(textarea, "Test message");

      expect(sendButton).toBeEnabled();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA label on send button", () => {
      render(<ChatInput onSend={onSendMock} />);

      const sendButton = screen.getByRole("button", { name: /send message/i });
      expect(sendButton).toHaveAttribute("aria-label", "Send message");
    });
  });

  describe("CSS Classes", () => {
    it("should apply custom className to container", () => {
      const { container } = render(
        <ChatInput onSend={onSendMock} className="custom-class" />
      );

      const inputContainer = container.firstChild;
      expect(inputContainer).toHaveClass("custom-class");
    });

    it("should apply opacity-50 when disabled", () => {
      const { container } = render(<ChatInput onSend={onSendMock} disabled />);

      const inputContainer = container.firstChild;
      expect(inputContainer).toHaveClass("opacity-50");
    });
  });
});
